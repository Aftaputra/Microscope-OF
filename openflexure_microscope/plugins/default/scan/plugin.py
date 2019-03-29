import time
import numpy as np
from typing import Tuple
import uuid
import logging

from openflexure_microscope.camera.base import generate_basename
from openflexure_microscope.plugins import MicroscopePlugin

from .api import TileScanAPI, ZStackAPI

def construct_grid(initial, step_sizes, n_steps, style='raster'):
    """
    Given an initial position, step sizes, and number of steps,
    construct a 2-dimensional list of scan x-y positions.
    """
    arr = []

    for i in range(n_steps[0]): # x axis
        arr.append([])
        for j in range(n_steps[1]): # y axis
            # Create a coordinate array
            coord = [initial[ax] + [i, j][ax]*step_sizes[ax] for ax in range(2)]
            # Append coordinate array to position grid
            arr[i].append(tuple(coord))

    # Style modifiers
    if style == 'snake':
        for i, line in enumerate(arr):
            if i % 2 != 0:
                line.reverse()

    return arr

def flatten_grid(grid):
    """
    Convert a 3D list of scan positions into a flat list
    of sequential positions. 
    """

    grid = list(itertools.chain(*grid))
    return grid

class ScanPlugin(MicroscopePlugin):
    """
    Stack and tile plugin
    """

    api_views = {
        '/tile': TileScanAPI,
        '/stack': ZStackAPI,
    }

    def capture(self,
                basename,
                scan_id,
                use_video_port: bool = False,
                resize: Tuple[int, int] = None,
                bayer: bool = False,
                metadata: dict = {},
                tags: list = []):

        # Construct a tile filename
        filename = "{}_{}_{}_{}".format(basename, *self.microscope.stage.position)
        foldername = "SCAN_{}".format(basename)

        # Create output object
        output = self.microscope.camera.new_image(
            write_to_file=True,
            temporary=False,
            filename=filename,
            folder=foldername)

        # Capture
        self.microscope.camera.capture(
            output,
            use_video_port=use_video_port,
            resize=resize,
            bayer=bayer)

        # Affix metadata
        if 'scan' not in tags:
            tags.append('scan')

        metadata.update({
            'position': self.microscope.state['stage']['position'],
            'scan_id': scan_id,
            'basename': basename,
        })

        output.put_metadata(metadata)
        output.put_tags(tags)

    def tile(
            self,
            basename: str = None,
            step_size: int = [2000, 1500, 100],
            grid: list = [3, 3, 5],
            style='raster',
            autofocus_dz: int = 50,
            use_video_port: bool = False,
            resize: Tuple[int, int] = None,
            bayer: bool = False,
            metadata: dict = {},
            tags: list = []):

        # Generate a basename if none given
        if not basename:
            basename = generate_basename()

        # Generate a stack ID
        scan_id = uuid.uuid4().hex

        # Store initial position
        initial_position = self.microscope.stage.position

        # Add scan metadata
        if not 'time' in metadata:
            metadata['time'] = generate_basename()

        # Check if autofocus is enabled
        if autofocus_dz and hasattr(self.microscope.plugin, 'default_autofocus'):
            autofocus_enabled = True
        else:
            autofocus_enabled = False

        # Construct an x-y grid (worry about z later)
        x_y_grid = construct_grid(
            initial_position, 
            step_size[:2], 
            grid[:2],
            style=style
        )

        # Now step through each point in the x-y coordinate array
        for line in x_y_grid:
            # If rastering, rather than snake (or eventually spiral)
            if style == 'raster':
                # Return focus to initial position
                logging.debug("Returning to initial z position")
                self.microscope.stage.move_abs([line[0][0], line[0][1], initial_position[2]])

            for x_y in line:
                current_position = self.microscope.stage.position
                # Move to new grid position without changing z
                logging.debug("Moving to step {}".format([x_y[0], x_y[1], current_position[2]]))
                self.microscope.stage.move_abs([x_y[0], x_y[1], current_position[2]])
                # Refocus
                if autofocus_enabled:
                    # TODO: Better autofocus
                    logging.debug("Running autofocus")
                    self.microscope.plugin.default_autofocus.autofocus(
                        range(-3 * autofocus_dz, 4 * autofocus_dz, autofocus_dz))
                    logging.debug("Finished autofocus")
                    time.sleep(1)  # TODO: Remove

                # If we're not doing a z-stack, just capture
                if (grid[2] <= 1):
                    self.capture(
                        basename,
                        scan_id,
                        use_video_port=use_video_port,
                        resize=resize,
                        bayer=bayer,
                        metadata=metadata,
                        tags=tags
                    )
                else:
                    logging.debug("Entering z-stack")
                    self.stack(
                        basename=basename,
                        scan_id=scan_id,
                        step_size=step_size[2],
                        steps=grid[2],
                        center=True,
                        use_video_port=use_video_port,
                        resize=resize,
                        bayer=bayer,
                        metadata=metadata,
                        tags=tags
                    )

        logging.debug("Returning to {}".format(initial_position))
        self.microscope.stage.move_abs(initial_position)

    def stack(
            self,
            basename: str = None,
            scan_id: str = None,
            step_size: int = 100,
            steps: int = 5,
            center: bool = True,
            use_video_port: bool = False,
            resize: Tuple[int, int] = None,
            bayer: bool = False,
            metadata: dict = {},
            tags: list = []):

        # Generate a basename if none given
        if not basename:
            basename = generate_basename()

        # Generate a stack ID
        if not scan_id:
            scan_id = uuid.uuid4().hex

        # Add scan metadata
        if not 'time' in metadata:
            metadata['time'] = generate_basename()

        # Store initial position
        initial_position = self.microscope.stage.position

        # Move to center scan
        if center:
            logging.debug("Moving to starting position")
            self.microscope.stage.move_rel([0, 0, int((-step_size * steps) / 2)])

        with self.microscope.lock:

            for i in range(steps):
                time.sleep(0.1)
                logging.debug("Capturing...")
                self.capture(
                    basename,
                    scan_id,
                    use_video_port=use_video_port,
                    resize=resize,
                    bayer=bayer,
                    metadata=metadata,
                    tags=tags
                )

                if i != steps - 1:
                    logging.debug("Moving z by {}".format(step_size))
                    self.microscope.stage.move_rel([0, 0, step_size])

            logging.debug("Returning to {}".format(initial_position))
            self.microscope.stage.move_abs(initial_position)
