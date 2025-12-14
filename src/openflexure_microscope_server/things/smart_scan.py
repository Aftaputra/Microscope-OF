"""The core sample scanning functionality for the OpenFlexure Microscope.

SmartScan provides sample scanning functionality including automatic background
detection (via the ``CameraThing``) and automatic path planning via
`scan_planners`. It manages the directories of past scans via `scan_directories`.
It also controls external processes for live stitching composite images, and
the creation of the final stitched images.
"""

import os
import threading
import time
from datetime import datetime
from subprocess import SubprocessError
from typing import (
    Any,
    Callable,
    Concatenate,
    Mapping,
    Optional,
    ParamSpec,
    Self,
    TypeVar,
)

import numpy as np
from fastapi import HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

import labthings_fastapi as lt

from openflexure_microscope_server import scan_directories, scan_planners, stitching

# Things
from .autofocus import AutofocusThing, StackParams
from .camera import CameraDependency as CameraClient
from .camera_stage_mapping import CameraStageMapper
from .stage import StageDependency as StageDep

T = TypeVar("T")
P = ParamSpec("P")

CSMDep = lt.deps.direct_thing_client_dependency(
    CameraStageMapper, "/camera_stage_mapping/"
)
AutofocusDep = lt.deps.direct_thing_client_dependency(AutofocusThing, "/autofocus/")


class ScanListInfo(BaseModel):
    """The information to be sent to the Scan List tab."""

    scans: list[scan_directories.ScanInfo]
    """The list of scans as ScanInfo objects"""

    ongoing: Optional[str]
    """The name of the ongoing scan or None"""


class JPEGBlob(lt.blob.Blob):
    """A class representing a JPEG image as a LabThings FastAPI Blob."""

    media_type: str = "image/jpeg"


class ZipBlob(lt.blob.Blob):
    """A class representing a Zip file as a LabThings FastAPI Blob."""

    media_type: str = "application/zip"


class ScanNotRunningError(RuntimeError):
    """Exception called when scan not running that requires a scan to be running."""


def _scan_running(
    method: Callable[Concatenate[Self, P], T],
) -> Callable[Concatenate[Self, P], T]:
    """Decorate a method so that it will error if a scan is not running.

    This decorator is used by all methods in SmartScanThing that are using
    the variables set for the scan. It will throw a runtime error if
    self._scan_logger is not set, as all scan variables are set at
    the same time and released with the lock
    """

    def scan_running_wrapper(self: Self, *args: P.args, **kwargs: P.kwargs) -> T:
        # Only start the method is the scan logger is set
        if self._scan_logger is not None:
            return method(self, *args, **kwargs)
        raise ScanNotRunningError(
            "Calling a @scan_running method can only be done while a scan is running!"
        )

    return scan_running_wrapper


class SmartScanThing(lt.Thing):
    """A Thing for scanning samples and interacting with past scans.

    SmartScanThing exposes all functionality for automatically scanning samples,
    previewing live stitching, retrieving data from past scans, and for deleting
    past scans.
    """

    def __init__(
        self, thing_server_interface: lt.ThingServerInterface, scans_folder: str
    ) -> None:
        """Initialise a SmartScanThing saving to and loading from the input directory.

        :param scans_folder: This is the path to the directory where all scans will be
            saved. Any scans already in this directory will be accessible through the
            HTTP interface.
        """
        super().__init__(thing_server_interface)
        self._scan_dir_manager = scan_directories.ScanDirectoryManager(scans_folder)
        self._scan_lock = threading.Lock()

        # Variables set by the scan
        self._latest_scan_name: Optional[str] = None

        # Scan logger is the invocation logger labthings-fastapi creates
        # when the `sample_scan` lt.action is called. It is saved as
        # private class variable along with many others here.
        # Access to these variables requires a scan to be running,
        # any method that calls these should be decorated with
        # @_scan_running
        self._scan_logger: Optional[lt.deps.InvocationLogger] = None
        self._cancel: Optional[lt.deps.CancelHook] = None
        self._autofocus: Optional[AutofocusDep] = None
        self._stage: Optional[StageDep] = None
        self._cam: Optional[CameraClient] = None
        self._csm: Optional[CSMDep] = None
        self._stack_params: Optional[StackParams] = None
        self._ongoing_scan: Optional[scan_directories.ScanDirectory] = None
        self._scan_data: Optional[scan_directories.ScanData] = None
        self._preview_stitcher: Optional[stitching.PreviewStitcher] = None

    @lt.action
    def sample_scan(
        self,
        cancel: lt.deps.CancelHook,
        logger: lt.deps.InvocationLogger,
        autofocus: AutofocusDep,
        stage: StageDep,
        cam: CameraClient,
        csm: CSMDep,
        scan_name: str = "",
    ) -> None:
        """Move the stage to cover an area, taking images that can be tiled together.

        The stage will move in a pattern that grows outwards from the starting point,
        stopping once it is surrounded by "background" (as detected by the
        camera Thing) or reaches the "max_range" measured in steps.
        """
        got_lock = self._scan_lock.acquire(timeout=0.1)
        if not got_lock:
            raise RuntimeError("Trying to run scan while scan is already running!")

        # Set private variables for this scan
        self._cancel = cancel
        self._scan_logger = logger
        self._autofocus = autofocus
        self._stage = stage
        self._cam = cam
        self._csm = csm
        # `scan_data` should already be None. This is added as a precaution as
        # the presence of `scan_data` is used during error handling to
        # determine whether the scan started.
        self._scan_data = None
        try:
            self._check_background_and_csm_set()
            self._ongoing_scan = self._scan_dir_manager.new_scan_dir(scan_name)
            self._latest_scan_name = self._ongoing_scan.name
            self._autofocus.looping_autofocus(dz=self.autofocus_dz, start="centre")
            self._run_scan()
        except Exception as e:
            # If _scan_data is set then scan started
            if self._scan_data is not None:
                self._return_to_starting_position()
                if not isinstance(e, scan_directories.NotEnoughFreeSpaceError):
                    # Don't stitch if drive is full (already logged)
                    self._scan_logger.info(
                        "Attempting to stitch and archive the images acquired so far."
                    )
                    self._perform_final_stitch()
            # Error must be raised so UI gives correct output
            raise e
        finally:
            # However the scan finishes, unset all variables and release lock
            self._cancel = None
            self._scan_logger = None
            self._autofocus = None
            self._stage = None
            self._cam = None
            self._csm = None
            self._ongoing_scan = None
            self._scan_data = None
            self._scan_lock.release()
            # Ensure any PreviewStitcher created cannot be reused.
            self._preview_stitcher = None
            self._stack_params = None

        # Remove any scan folders containing zero images.
        self.purge_empty_scans(logger=logger)

    @_scan_running
    def _check_background_and_csm_set(self) -> None:
        """Before starting a scan, check that background and camera-stage-mapping are set.

        Raise error if:
          - background is to be skipped but is not set
          - camera stage mapping is not set

        Raise warning if not using background detect that scan will go on until max steps reached
        """
        if self._csm.image_resolution is None:
            raise RuntimeError(
                "Camera-stage mapping is not calibrated. This is required before "
                "scans can be carried out."
            )

        if self.skip_background:
            if not self._cam.background_detector_status.ready:
                raise RuntimeError(
                    "Background is not set: you need to calibrate background detection."
                )
        else:
            self._scan_logger.warning(
                "This scan will run in a spiral from the starting point "
                f"until you cancel it, or until it has moved by {self.max_range} steps "
                "in every direction. Make sure you watch it run to stop it leaving "
                "the area of interest, or (worse) leading the microscope's range "
                "of motion."
            )

    @lt.property
    def latest_scan_name(self) -> Optional[str]:
        """The name of the last scan to be started."""
        return self._latest_scan_name

    @_scan_running
    def _move_to_next_point(
        self, next_point: tuple[int, int], z_estimate: Optional[int] = None
    ) -> tuple[int, int, int]:
        """Move the stage to the next position.

        If no z_estimate is given then the current stage position is used. Must move
        to the estimated focused position (although moving below would be marginally
        faster) because background detect is most reliable at the focused position.

        :returns: the (x,y,z) with the chosen z_estimate
        """
        if z_estimate is None:
            z_estimate = self._stage.position["z"]

        self._scan_logger.info(f"Moving to {next_point}")
        self._stage.move_absolute(
            x=next_point[0],
            y=next_point[1],
            z=z_estimate,
        )

        return (next_point[0], next_point[1], z_estimate)

    @_scan_running
    def _calc_displacement_from_test_image(self, overlap: int) -> tuple[int, int]:
        """Take a test image and use camera stage mapping to calculate x and y displacement.

        :param overlap: The desired overlap as a fraction of the image. i.e. 0.5 means
            that each image should overlap its nearest neighbour by 50%.

        :returns: (dx, dy) - the x and y displacements in steps
        """
        test_image = self._cam.grab_as_array()

        test_image_res = list(test_image.shape)
        csm_image_res = [int(i) for i in self._csm.image_resolution]

        # If current stream width is different to csm calibration width,
        # perform the conversion here
        res_ratio = csm_image_res[0] / test_image_res[0]

        # get displacement matrix. note it is for (y, x) not (x, y) coordinates
        csm_disp_matrix = np.array(self._csm.image_to_stage_displacement_matrix)
        csm_disp_matrix *= res_ratio

        # Calculate displacements in image coordinates
        dx_img = test_image.shape[1] * (1 - overlap)
        dy_img = test_image.shape[0] * (1 - overlap)

        # Calculate displacements in steps as vectors using a dot product with the matrix
        dx_vec = np.dot(np.array([0, dx_img]), csm_disp_matrix)
        dy_vec = np.dot(np.array([dy_img, 0]), csm_disp_matrix)

        # Assume no rotation or skew and take only the aligned axis of vector.
        # Coerce to positive integer
        dx = int(np.abs(dx_vec[0]))
        dy = int(np.abs(dy_vec[1]))

        return dx, dy

    @_scan_running
    def _collect_scan_data(self) -> scan_directories.ScanData:
        """Collect and return the data for this scan so it cannot be changed mid-scan."""
        # Record starting position so it can be returned to at end of scan.
        starting_position = self._stage.position
        overlap = self.overlap
        dx, dy = self._calc_displacement_from_test_image(overlap)
        correlation_resize = stitching.STITCHING_RESOLUTION[0] / self.save_resolution[0]

        self._scan_logger.debug(
            f"Resizing images when correlating by a factor of {correlation_resize}"
        )

        self._scan_logger.info(
            f"Based on an overlap of {overlap}, we will make steps of {dx}, {dy}"
        )

        autofocus_dz = self.autofocus_dz
        if autofocus_dz == 0:
            self._scan_logger.info("Running scan without autofocus")
        elif autofocus_dz <= 200:
            self._scan_logger.warning(
                f"Your autofocus range is {autofocus_dz} steps, which is too short to "
                "attempt to focus. Running without autofocus"
            )
            autofocus_dz = 0

        # Fix scan parameters in case UI is updated during scan.
        return scan_directories.ScanData(
            scan_name=self._ongoing_scan.name,
            starting_position=starting_position,
            overlap=overlap,
            max_dist=self.max_range,
            dx=dx,
            dy=dy,
            autofocus_dz=autofocus_dz,
            autofocus_on=bool(autofocus_dz),
            start_time=datetime.now(),
            skip_background=self.skip_background,
            stitch_automatically=self.stitch_automatically,
            correlation_resize=correlation_resize,
            save_resolution=self.save_resolution,
        )

    @_scan_running
    def _save_final_scan_data(self, scan_result: str) -> None:
        """Update scan data JSON file with data only known at the end of the scan.

        Takes scan_result, a string that is either "success", "cancelled by user",
        or the error that ended the scan.
        """
        self._scan_data.set_final_data(result=scan_result)
        self._ongoing_scan.save_scan_data(self._scan_data)

    @_scan_running
    def _manage_stitching_threads(self) -> None:
        """Manage the stitching threads, starting them if needed and not already running."""
        # Assume 4 images means at least one offset in x and y, making the stitching
        # well constrained.
        if self._scan_data.image_count > 3 and not self._preview_stitcher.running:
            self._preview_stitcher.start()

    @_scan_running
    def _run_scan(self) -> None:
        """Prepare and run the main scan, and perform final actions on completion.

        The result (or exception) from the main scan loop determines whether the
        scan should be stitched and whether  the microscope should return to the
        starting x,y,z position.
        """
        try:
            self._cam.start_streaming(main_resolution=(3280, 2464))
            self._scan_data = self._collect_scan_data()
            self._ongoing_scan.save_scan_data(self._scan_data)
            self._stack_params = self._autofocus.create_stack_params(
                images_dir=self._ongoing_scan.images_dir,
                autofocus_dz=self.autofocus_dz,
                save_resolution=self._scan_data.save_resolution,
                logger=self._scan_logger,
            )
            self._preview_stitcher = stitching.PreviewStitcher(
                self._ongoing_scan.images_dir,
                overlap=self._scan_data.overlap,
                correlation_resize=self._scan_data.correlation_resize,
            )

            # This is the main loop of the scan!
            self._main_scan_loop()
            self._save_final_scan_data(scan_result="success")

        except lt.exceptions.InvocationCancelledError:
            # Reset the cancel event so it can be thrown again
            self._cancel.clear()
            self._scan_logger.info("Stopping scan because it was cancelled.")
            self._save_final_scan_data(scan_result="cancelled by user")
        except Exception as e:
            err_name = type(e).__name__
            if self._scan_data is not None:
                self._save_final_scan_data(scan_result=f"{err_name}: {e}")
            self._scan_logger.error(
                f"The scan stopped because of an error: {e}",
                exc_info=e,
            )
            raise e
        finally:
            # Don't set Preview Stitcher to None yet. It is used by
            # _perform_final_stitch, which may also be run after this function completes
            # if it ended due to an exception.

            # Start streaming in the default resolution again as soon as possible
            self._cam.start_streaming()

        # This is what happens if the scan completes successfully or the
        # user cancels it.
        self._return_to_starting_position()
        self._perform_final_stitch()

    @_scan_running
    def _main_scan_loop(self) -> None:
        """Run the main loop of the scan.

        This loop runs during a scan, until no more scan x,y positions
        are remaining.
        """
        # The initial plan for the scan should be a single x,y position. All future
        # moves will be planned around this point. In future, route planner could
        # have multiple starting positions, each of which will be visited before the
        # scan can end.
        planner_settings = {
            "dx": self._scan_data.dx,
            "dy": self._scan_data.dy,
            "max_dist": self._scan_data.max_dist,
        }
        route_planner = scan_planners.SmartSpiral(
            initial_position=(self._stage.position["x"], self._stage.position["y"]),
            planner_settings=planner_settings,
        )

        # The loop tests if the scan should continue, moves to the next position,
        # decides whether to capture an image, autofocuses if necessary,
        # captures an image if necessary, updates the scan path and future path,
        # and updates the zip file with new images.
        while not route_planner.scan_complete:
            self._scan_dir_manager.check_free_disk_space()
            self._manage_stitching_threads()

            next_pos_xy, z_est = route_planner.get_next_location_and_z_estimate()
            new_pos_xyz = self._move_to_next_point(next_pos_xy, z_est)
            current_pos_xyz = (
                new_pos_xyz[0],
                new_pos_xyz[1],
                self._stage.position["z"],
            )

            capture_image = True
            # If skipping background, take an image to check if current field of view is background
            if self._scan_data.skip_background:
                capture_image, bg_message = self._cam.image_is_sample()

            if not capture_image:
                route_planner.mark_location_visited(
                    new_pos_xyz, imaged=False, focused=False
                )
                msg = f"Skipping {new_pos_xyz} as it is {bg_message}."
                self._scan_logger.info(msg)
                continue

            focused, focused_height = self._autofocus.run_smart_stack(
                stack_parameters=self._stack_params,
                save_on_failure=not self._scan_data.skip_background,
            )

            current_pos_xyz = (new_pos_xyz[0], new_pos_xyz[1], focused_height)

            # An image was captured if we are focussed or we are not skipping background.
            imaged = focused or not self._scan_data.skip_background

            route_planner.mark_location_visited(
                current_pos_xyz, imaged=imaged, focused=focused
            )

            # increment capture counter as thread has completed
            self._scan_data.image_count += 1
            # Add it to the incremental zip
            self._ongoing_scan.zip_files()

    @_scan_running
    def _return_to_starting_position(self) -> None:
        """Return to the initial scan position, if set."""
        self._scan_logger.info("Returning to starting position.")
        if self._scan_data is not None:
            self._stage.move_absolute(
                **self._scan_data.starting_position, block_cancellation=True
            )

    @property
    def thing_state(self) -> Mapping[str, Any]:
        """Return a metadata dict for ongoing scan to populate."""
        if self._ongoing_scan is None:
            return {}
        return {"scan_name": self._ongoing_scan.name}

    @_scan_running
    def _perform_final_stitch(self) -> None:
        """Update the scan zip and perform final stitch of the data."""
        if self._scan_data.image_count <= 3:
            self._scan_logger.info("Not performing a stitch as 3 or fewer images taken")
            return

        self._ongoing_scan.zip_files()

        self._scan_logger.info("Waiting for background processes to finish...")

        if self._preview_stitcher is not None:
            self._preview_stitcher.wait(self._cancel)

        if self._scan_data.stitch_automatically:
            self._scan_logger.info("Stitching final image (may take some time)...")
            self.stitch_scan(
                logger=self._scan_logger,
                cancel=self._cancel,
                scan_name=self._ongoing_scan.name,
                correlation_resize=self._scan_data.correlation_resize,
                overlap=self._scan_data.overlap,
            )

    @lt.endpoint(
        "get",
        "scans/stitched_thumbnail.jpg",
        responses={
            200: {
                "description": "A thumbnail-quality stitched image",
                "content": {"image/jpeg": {}},
            },
            404: {"description": "File not found"},
        },
    )
    def get_scan_thumbnail(self, scan_name: str) -> FileResponse:
        """Retrieve a file from a scan.

        This endpoint allows files to be downloaded from a scan.
        """
        preview_path = self._scan_dir_manager.get_file_path_from_img_dir(
            scan_name=scan_name, filename="stitched_thumbnail.jpg", check_exists=True
        )
        if preview_path is None:
            raise HTTPException(404, "File not found")
        return FileResponse(preview_path)

    save_resolution: tuple[int, int] = lt.setting(default=(1640, 1232))
    """A tuple of the image resolution to capture."""

    max_range: int = lt.setting(default=45000)
    """The maximum distance in steps from the centre of the scan."""

    stitch_tiff: bool = lt.setting(default=False)
    """Whether or not to also produce a pyramidal tiff at the end of a scan."""

    skip_background: bool = lt.setting(default=True)
    """Whether to detect and skip empty fields of view.

    This uses the settings from the ``BackgroundDetectThing``."""

    autofocus_dz: int = lt.setting(default=1000)
    """The z distance to perform an autofocus in steps."""

    overlap: float = lt.setting(default=0.45)
    """The fraction (0-1) that adjacent images should overlap in x or y."""

    stitch_automatically: bool = lt.setting(default=True)
    """Whether to run a final stitch at the end of a successful scan."""

    def _get_all_scan_info(self) -> list[scan_directories.ScanInfo]:
        """Return all the information from the scan directories.

        It is preferable to use the method rather than calling
        _scan_dir_manager.all_scans_info() directly as it will handle stopping the json
        in any ongoing scans being read.
        """
        ongoing_name = None if self._ongoing_scan is None else self._ongoing_scan.name
        return self._scan_dir_manager.all_scans_info(ongoing=ongoing_name)

    @lt.property
    def scans(self) -> ScanListInfo:
        """All the available scans.

        Each scan has a name (which can be used to access it), along with
        its modified and created times (according to the filesystem) and
        the number of items in the ``images`` folder. Note that image count
        uses a regular expression, and changes to the naming scheme will
        break it.
        """
        return ScanListInfo(
            scans=self._get_all_scan_info(),
            ongoing=None if self._ongoing_scan is None else self._ongoing_scan.name,
        )

    @lt.endpoint(
        "get",
        "get_stitch/{scan_name}",
        responses={
            200: {
                "description": "Successfully downloading file",
                "content": {"*/*": {}},
            },
            403: {"description": "Filename not permitted"},
            404: {"description": "File not found"},
        },
    )
    def get_stitch_file(self, scan_name: str) -> FileResponse:
        """Return the stitched image corresponding to a given scan name, if it exists.

        Will only return a file ending in suffix STITCH_SUFFIX
        Note: when downloading this, the default filename will be ``scan_name``.jpeg
        """
        stitch_path = self._scan_dir_manager.get_final_stitch_path(scan_name)

        if stitch_path is None:
            raise HTTPException(404, "File not found")
        return FileResponse(stitch_path)

    @lt.endpoint(
        "delete",
        "scans/{scan_name}",
        responses={
            200: {"description": "Successfully deleted scan"},
            400: {"description": "An error occurred while trying to delete scan"},
        },
    )
    def delete_scan(self, scan_name: str, logger: lt.deps.InvocationLogger) -> None:
        """Delete the folder for the specified scan.

        This endpoint allows scans to be deleted from disk.

        Takes the scan name to delete, and the Invocation Logger
        """
        if not self._scan_dir_manager.exists(scan_name):
            logger.warning(f"Cannot find a scan of name {scan_name}")
            raise HTTPException(400, "Scan not found")
        deleted_scan_success = self._delete_scan(scan_name, logger)
        if not deleted_scan_success:
            raise HTTPException(400, "Couldn't delete scan, check log for details")

    @lt.endpoint(
        "delete",
        "scans",
    )
    def delete_all_scans(self, logger: lt.deps.InvocationLogger) -> None:
        """Delete all the scans on the microscope.

        **This will irreversibly remove all scanned data from the
        microscope!**
        Use with extreme caution.
        """
        for scan_name in self._scan_dir_manager.all_scans:
            self._delete_scan(scan_name, logger)

    @lt.action
    def purge_empty_scans(self, logger: lt.deps.InvocationLogger) -> None:
        """Delete all scan folders containing no images at the top level."""
        # JSON is ignored as it's created before any images are captured
        for scan_info in self._get_all_scan_info():
            if scan_info.number_of_images == 0:
                self._delete_scan(scan_info.name, logger)

    def _delete_scan(self, scan_name: str, logger: lt.deps.InvocationLogger) -> bool:
        """Delete a scan.

        This is a wrapper around scan manager's delete_scan that logs to the
        invocation logger id there is a problem.
        """
        if self._ongoing_scan is not None and scan_name == self._ongoing_scan.name:
            logger.error("Attempted to delete ongoing scan.")
            return False
        try:
            self._scan_dir_manager.delete_scan(scan_name)
            return True
        except Exception as e:
            logger.warning(
                "Attempted to delete scan " + scan_name + ", which failed."
                " Server sent response" + str(e)
            )
            return False

    @property
    def latest_preview_stitch_path(self) -> Optional[str]:
        """The path of the latest preview stitched image, or None if not available."""
        if not self.latest_scan_name:
            return None

        return self._scan_dir_manager.get_file_path_from_img_dir(
            scan_name=self.latest_scan_name, filename="preview.jpg", check_exists=True
        )

    @lt.property
    def latest_preview_stitch_time(self) -> Optional[float]:
        """The modification time of the latest preview image, to allow live updating.

        This will return None (``null`` to JS) if there is no preview image to return.

        This is used for two reasons:

        1. If all caching was turned off this stitch would be sent over the network
           repeatedly
        2. If caching was is on, then the stitch will not update when needed.
        """
        if self.latest_preview_stitch_path is None:
            return None
        return os.path.getmtime(self.latest_preview_stitch_path)

    @lt.endpoint(
        "get",
        "latest_preview_stitch.jpg",
        responses={
            200: {
                "description": "A preview-quality stitched image",
                "content": {"image/jpeg": {}},
            },
            404: {"description": "File not found"},
        },
    )
    def get_latest_preview(self) -> FileResponse:
        """Retrieve the latest preview image."""
        preview_path = self.latest_preview_stitch_path
        if preview_path is None:
            raise HTTPException(404, "File not found")
        return FileResponse(preview_path)

    @lt.action
    def stitch_scan(
        self,
        logger: lt.deps.InvocationLogger,
        cancel: lt.deps.CancelHook,
        scan_name: str,
        correlation_resize: Optional[float] = None,
        overlap: Optional[float] = None,
    ) -> None:
        """Generate a stitched image based on stage position metadata.

        Note that as this is a lt.action it needs the logger passed as
        a variable if called from another thing action
        """
        scan_data_dict = self._scan_dir_manager.get_scan_data_dict(scan_name)
        if scan_data_dict is None:
            logger.warning("Couldn't read scan data - it may be missing or corrupt.")
        final_stitcher = stitching.FinalStitcher(
            self._scan_dir_manager.img_dir_for(scan_name),
            logger=logger,
            overlap=overlap,
            correlation_resize=correlation_resize,
            stitch_tiff=self.stitch_tiff,
            scan_data_dict=scan_data_dict,
        )
        try:
            # start the final stitch, providing the cancel hook to allow aborting
            final_stitcher.run(cancel)
        except lt.exceptions.InvocationCancelledError:
            # Sleep for 1 second just to allow invocation logs to pass to user.
            time.sleep(1)
        except SubprocessError as e:
            self._scan_logger.error(f"Stitching failed: {e}", exc_info=e)

    @lt.action
    def download_zip(
        self,
        scan_name: str,
    ) -> ZipBlob:
        """Return zip after including any files left until the end.

        The zipfile is returned as a Blob.
        """
        zip_fname = self._scan_dir_manager.zip_scan(scan_name, final_version=True)
        return ZipBlob.from_file(zip_fname)

    @lt.action
    def stitch_all_scans(
        self, logger: lt.deps.InvocationLogger, cancel: lt.deps.CancelHook
    ) -> None:
        """Check the list of scans, and stitch any that don't have a DZI associated with it.

        :raises RuntimeError: if the microscope is currently running a scan

        """
        if self._scan_logger is not None:
            raise RuntimeError("Can't stitch previous scans while a scan is ongoing")
        for scan in self._get_all_scan_info():
            if scan.dzi is None:
                self.stitch_scan(logger=logger, cancel=cancel, scan_name=scan.name)
