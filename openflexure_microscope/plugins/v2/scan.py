import numpy as np
import itertools
import logging
import uuid
from typing import Tuple
from functools import reduce

from openflexure_microscope.camera.base import generate_basename
from openflexure_microscope.common.flask_labthings.find import find_device, find_plugin
from openflexure_microscope.common.flask_labthings.plugins import BasePlugin

from openflexure_microscope.devel import (
    JsonResponse,
    request,
    jsonify,
    taskify,
    abort,
    update_task_progress,
    update_task_data,
)

from openflexure_microscope.common.flask_labthings.resource import Resource
import time


### Grid construction


def construct_grid(initial, step_sizes, n_steps, style="raster"):
    """
    Given an initial position, step sizes, and number of steps,
    construct a 2-dimensional list of scan x-y positions.
    """
    arr = []

    for i in range(n_steps[0]):  # x axis
        arr.append([])
        for j in range(n_steps[1]):  # y axis
            # Create a coordinate array
            coord = [initial[ax] + [i, j][ax] * step_sizes[ax] for ax in range(2)]
            # Append coordinate array to position grid
            arr[i].append(tuple(coord))

    # Style modifiers
    if style == "snake":
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


### Progress

_images_to_be_captured: int = 1
_images_captured_so_far: int = 0


def progress():
    progress = (_images_captured_so_far / _images_to_be_captured) * 100
    logging.info(progress)
    return progress


### Capturing


def capture(
    microscope,
    basename,
    scan_id,
    temporary: bool = False,
    use_video_port: bool = False,
    resize: Tuple[int, int] = None,
    bayer: bool = False,
    metadata: dict = {},
    tags: list = [],
):

    # Construct a tile filename
    filename = "{}_{}_{}_{}".format(basename, *microscope.stage.position)
    folder = "SCAN_{}".format(basename)

    # Create output object
    output = microscope.camera.new_image(
        temporary=temporary, filename=filename, folder=folder
    )

    # Capture
    microscope.camera.capture(
        output.file, use_video_port=use_video_port, resize=resize, bayer=bayer
    )

    # Affix metadata
    if "scan" not in tags:
        tags.append("scan")

    # Inject system metadata
    output.put_metadata(microscope.metadata, system=True)

    # Insert custom metadata
    output.put_metadata(metadata)

    # Insert custom tags
    output.put_tags(tags)


### Scanning


def tile(
    microscope,
    basename: str = None,
    temporary: bool = False,
    step_size: int = [2000, 1500, 100],
    grid: list = [3, 3, 5],
    style="raster",
    autofocus_dz: int = 50,
    use_video_port: bool = False,
    resize: Tuple[int, int] = None,
    bayer: bool = False,
    fast_autofocus=False,
    metadata: dict = {},
    tags: list = [],
):
    global _images_to_be_captured
    global _images_captured_so_far

    # Keep task progress
    # TODO: Make this line not nasty
    _images_to_be_captured = reduce((lambda x, y: x * y), grid)
    _images_captured_so_far = 0

    # Generate a basename if none given
    if not basename:
        basename = generate_basename()

    # Generate a stack ID
    scan_id = uuid.uuid4()

    # Store initial position
    initial_position = microscope.stage.position

    # Add scan metadata
    if "time" not in metadata:
        metadata["time"] = generate_basename()

    metadata.update(
        {
            "scan_id": scan_id,
            "basename": basename,
            "scan_parameters": {
                "step_size": step_size,
                "grid": grid,
                "style": style,
                "autofocus_dz": autofocus_dz,
            },
        }
    )

    # Check if autofocus is enabled
    autofocus_plugin = find_plugin("autofocus")
    if (
        autofocus_dz
        and autofocus_plugin
        and microscope.has_real_stage()
        and microscope.has_real_camera()
    ):
        autofocus_enabled = True
    else:
        autofocus_enabled = False

    z_stack_dz = (
        grid[2] * step_size[2] if grid[2] > 1 else 0
    )  # shorthand for Z stack range

    # Construct an x-y grid (worry about z later)
    x_y_grid = construct_grid(initial_position, step_size[:2], grid[:2], style=style)

    # Keep the initial Z position the same as our current position
    next_z = initial_position[2]
    if fast_autofocus:  # If fast autofocus is enabled, make
        next_z += autofocus_dz / 2  # sure we start from the top of the range
    initial_z = next_z  # Save this value for use in raster scans

    # Now step through each point in the x-y coordinate array
    for line in x_y_grid:
        # If rastering, rather than snake (or eventually spiral)
        # Return focus to initial position
        if style == "raster":
            next_z = initial_z
            logging.debug("Returning to initial z position")
            microscope.stage.move_abs(
                [line[0][0], line[0][1], next_z]
            )  # RWB: I think this line is redundant

        for x_y in line:
            # Move to new grid position without changing z
            logging.debug("Moving to step {}".format([x_y[0], x_y[1], next_z]))
            microscope.stage.move_abs([x_y[0], x_y[1], next_z])
            # Refocus
            if autofocus_enabled:
                if fast_autofocus:
                    autofocus_plugin.fast_autofocus(
                        dz=autofocus_dz,
                        target_z=-z_stack_dz / 2.0,  # Finish below the focus
                        initial_move_up=False,  # We're already at the top of the scan
                    )
                    # TODO: save the focus data for future reference? Use it for diagnostics?
                else:
                    logging.debug("Running autofocus")
                    autofocus_plugin.autofocus(
                        range(-3 * autofocus_dz, 4 * autofocus_dz, autofocus_dz)
                    )
                    logging.debug("Finished autofocus")
                    time.sleep(1)  # TODO: Remove

            # If we're not doing a z-stack, just capture
            if grid[2] <= 1:
                capture(
                    microscope,
                    basename,
                    scan_id,
                    temporary=temporary,
                    use_video_port=use_video_port,
                    resize=resize,
                    bayer=bayer,
                    metadata=metadata,
                    tags=tags,
                )
                # Update task progress
                _images_captured_so_far += 1
                update_task_progress(progress())
            else:
                logging.debug("Entering z-stack")
                stack(
                    microscope=microscope,
                    basename=basename,
                    temporary=temporary,
                    scan_id=scan_id,
                    step_size=step_size[2],
                    steps=grid[2],
                    center=not fast_autofocus,  # fast_autofocus does this for us!
                    return_to_start=not fast_autofocus,
                    use_video_port=use_video_port,
                    resize=resize,
                    bayer=bayer,
                    metadata=metadata,
                    tags=tags,
                )
            # Make sure we use our current best estimate of focus (i.e. the current position) next point
            next_z = microscope.stage.position[2]
            if fast_autofocus:
                next_z += (
                    autofocus_dz / 2
                )  # Fast autofocus requires us to start at the top of the range
                if grid[2] > 1:
                    next_z -= int(
                        grid[2] / 2.0 * step_size[2]
                    )  # Z stacking means we're higher up to start with

    logging.debug("Returning to {}".format(initial_position))
    microscope.stage.move_abs(initial_position)


def stack(
    microscope,
    basename: str = None,
    temporary: bool = False,
    scan_id: str = None,
    step_size: int = 100,
    steps: int = 5,
    center: bool = True,
    return_to_start: bool = True,
    use_video_port: bool = False,
    resize: Tuple[int, int] = None,
    bayer: bool = False,
    metadata: dict = {},
    tags: list = [],
):
    global _images_captured_so_far

    # Generate a basename if none given
    if not basename:
        basename = generate_basename()

    # Generate a stack ID
    if not scan_id:
        scan_id = uuid.uuid4()

    # Add scan metadata
    if not "time" in metadata:
        metadata["time"] = generate_basename()

    # Store initial position
    initial_position = microscope.stage.position

    with microscope.lock:
        # Move to center scan
        if center:
            logging.debug("Moving to starting position")
            microscope.stage.move_rel([0, 0, int((-step_size * steps) / 2)])

        for i in range(steps):
            time.sleep(0.1)
            logging.debug("Capturing...")
            capture(
                microscope,
                basename,
                scan_id,
                temporary=temporary,
                use_video_port=use_video_port,
                resize=resize,
                bayer=bayer,
                metadata=metadata,
                tags=tags,
            )
            # Update task progress
            _images_captured_so_far += 1
            update_task_progress(progress())

            if i != steps - 1:
                logging.debug("Moving z by {}".format(step_size))
                microscope.stage.move_rel([0, 0, step_size])
        if return_to_start:
            logging.debug("Returning to {}".format(initial_position))
            microscope.stage.move_abs(initial_position)


### Web views


class TileScanAPI(Resource):
    def post(self):
        payload = JsonResponse(request)
        microscope = find_device("openflexure_microscope")

        if not microscope:
            abort(503, "No microscope connected. Unable to autofocus.")

        # Get params
        filename = payload.param("filename")
        temporary = payload.param("temporary", default=False, convert=bool)

        step_size = payload.param("step_size", default=[2000, 1500, 100], convert=list)
        step_size = [int(i) for i in step_size]

        grid = payload.param("grid", default=[3, 3, 5], convert=list)
        grid = [int(i) for i in grid]

        style = payload.param("style", default="raster", convert=str)
        autofocus_dz = payload.param("autofocus_dz", default=50, convert=int)
        fast_autofocus = payload.param("fast_autofocus", default=False, convert=bool)

        use_video_port = payload.param("use_video_port", default=True, convert=bool)
        resize = payload.param("size", default=None)
        if resize:
            if ("width" in resize) and ("height" in resize):
                resize = (
                    int(resize["width"]),
                    int(resize["height"]),
                )  # Convert dict to tuple
            else:
                abort(404)

        bayer = payload.param("bayer", default=False, convert=bool)
        metadata = payload.param("metadata", default={}, convert=dict)
        tags = payload.param("tags", default=[], convert=list)

        logging.info("Running tile scan...")
        task = taskify(tile)(
            microscope,
            basename=filename,
            temporary=temporary,
            step_size=step_size,
            grid=grid,
            style=style,
            autofocus_dz=autofocus_dz,
            use_video_port=use_video_port,
            resize=resize,
            bayer=bayer,
            fast_autofocus=fast_autofocus,
            metadata=metadata,
            tags=tags,
        )

        # return a handle on the scan task
        return jsonify(task.state), 201


scan_plugin_v2 = BasePlugin("scan")

scan_plugin_v2.add_view(TileScanAPI, "/tile")
scan_plugin_v2.register_action(TileScanAPI)
