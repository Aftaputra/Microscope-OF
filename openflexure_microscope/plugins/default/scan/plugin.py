import time
import numpy as np
from typing import Tuple
import uuid

from openflexure_microscope.camera.base import generate_basename
from openflexure_microscope.plugins import MicroscopePlugin
from openflexure_microscope.utilities import set_properties


class ScanPlugin(MicroscopePlugin):
    """
    Stack and tile plugin
    """

    api_views = {}

    def capture(self,
                   basename,
                   scan_id,
                   use_video_port: bool = False,
                   resize: Tuple[int, int] = None,
                   bayer: bool = False):

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
        metadata = {}
        tags = ['stack']

        metadata.update({
            'Position': self.microscope.state['stage']['position'],
            'Stack ID': scan_id
        })

        output.put_metadata(metadata)
        output.put_tags(tags)

    def tile(
            self,
            basename: str = None,
            step_size: int = [2000, 1500],
            grid: list = [3, 3],
            autofocus_dz: int = 20,
            use_video_port: bool = False,
            resize: Tuple[int, int] = None,
            bayer: bool = False):

        # Generate a basename if none given
        if not basename:
            basename = generate_basename()

        # Generate a stack ID
        scan_id = uuid.uuid4().hex

        # Store initial position
        initial_position = self.microscope.stage.position

        # Check if autofocus is enabled
        if autofocus_dz and hasattr(self.microscope.plugin, 'default_autofocus'):
            autofocus_enabled = True
        else:
            autofocus_enabled = False

        xdirection = 1

        with self.microscope.lock:

            for i in range(grid[0]):
                for j in range(grid[1]):

                    if autofocus_enabled:
                        self.microscope.plugin.default_autofocus.autofocus(range(-2*autofocus_dz, 3*autofocus_dz, autofocus_dz))

                    self.capture(
                        basename,
                        scan_id,
                        use_video_port=use_video_port,
                        resize=resize,
                        bayer=bayer
                    )

                    if j != grid[0] - 1:
                        self.microscope.stage.move_rel([step_size[0]*xdirection, 0, 0])

                xdirection *= -1
                if i != grid[1] - 1:
                    self.microscope.stage.move_rel([256*xdirection, step_size[1], 0])

            self.microscope.stage.move_abs(initial_position)

    def stack(
            self,
            basename: str = None,
            step_size: int = 100,
            steps: list = 5,
            center: bool = True,
            use_video_port: bool = False,
            resize: Tuple[int, int] = None,
            bayer: bool = False):

        # Generate a basename if none given
        if not basename:
            basename = generate_basename()

        # Generate a stack ID
        scan_id = uuid.uuid4().hex

        # Store initial position
        initial_position = self.microscope.stage.position

        # Move to center scan
        if center:
            self.microscope.stage.move_rel([0, 0, int((-step_size * steps)/2)])

        with self.microscope.lock:

            for i in range(steps):

                self.capture(
                    basename,
                    scan_id,
                    use_video_port=use_video_port,
                    resize=resize,
                    bayer=bayer
                )

                if i != steps - 1:
                    self.microscope.stage.move_rel([0, 0, step_size])

            self.microscope.stage.move_abs(initial_position)
