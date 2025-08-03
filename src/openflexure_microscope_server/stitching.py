"""Communicate with OpenFlexure Stitching to perform stitches for scans.

This includes both live stitching and final stitching. This is done via subprocess
to call openflexure-stitching over CLI. This cannot be done via Threading dut to the
CPU intensity of stitching causing scanning problems due to the Python Global
Interpreter Lock (GIL). May be possible to shift to multiprocessing int the future.
"""

from typing import Optional, Any
import threading
import subprocess
import os
import time

import labthings_fastapi as lt

STITCHING_CMD = "openflexure-stitch"
STITCHING_RESOLUTION = (820, 616)

DEFAULT_OVERLAP = 0.5
DEFAULT_RESIZE = 0.5


class BaseStitcher:
    """A base stitching class for all stitchers. Don't initialise this directly."""

    def __init__(self, images_dir: str, *, overlap: float, correlation_resize: float):
        """Initialise a stitcher.

        All args except images_dir are positional only.

        :param images_dir: The images directory of the scan to stitch.
        :param overlap: The scan overlap.
        :param correlation_resize: The fraction to resize images by when correlating.
        """
        # Set minimum overlap to 90% of the scan overlap to catch only images
        # directly adjacent, not images with overlapping corners.
        self.images_dir = images_dir
        self.min_overlap = round(overlap * 0.9, 2)
        self.correlation_resize = correlation_resize
        self._mode = "all"
        self._extra_args = []

    @property
    def command(self) -> list[str]:
        """The command to run with subprocess.Popen."""
        # The command, and the mode
        initial_args = [STITCHING_CMD, "--stitching_mode", self._mode]
        setting_args = [
            "--minimum_overlap",
            f"{self.min_overlap}",
            "--resize",
            f"{self.correlation_resize}",
        ]
        return initial_args + self._extra_args + setting_args + [self.images_dir]

    def start(self) -> None:
        """Start stitching a stitching process.

        This should be overridden by any child class.
        """
        raise NotImplementedError(
            "Child stitchers should implement their own ``start`` method."
        )


class PreviewStitcher(BaseStitcher):
    """A stitcher for stitching an ongoing scan in preview mode.

    Use ``start()`` to start a scan, and ``running`` to check if it is complete, or
    ``wait()`` to wait for it to complete.

    The same stitcher object can be run multiple times to update the preview. However,
    one preview must finish before another can be started.
    """

    def __init__(self, images_dir: str, *, overlap: float, correlation_resize: float):
        """Initialise a preview stitcher.

        All args except images_dir are positional only.

        :param images_dir: The images directory of the scan to stitch.
        :param overlap: The scan overlap.
        :param correlation_resize: The fraction to resize images by when correlating.
        """
        super().__init__(
            images_dir, overlap=overlap, correlation_resize=correlation_resize
        )
        self._popen_lock = threading.Lock()
        self._popen_obj: Optional[subprocess.Popen] = None

        self._mode = "preview_stitch"

    @property
    def command(self) -> list[str]:
        """The command to run with subprocess.Popen."""
        return [
            STITCHING_CMD,
            "--stitching_mode",
            "preview_stitch",
            "--minimum_overlap",
            f"{self.min_overlap}",
            "--resize",
            f"{self.correlation_resize}",
            self.images_dir,
        ]

    def start(self) -> None:
        """Start stitching a preview of the scan in a background subprocess.

        This uses popen and returns immediately.
        """
        if self.running:
            raise RuntimeError("Cannot start stitch. It is already running.")
        with self._popen_lock:
            self._popen_obj = subprocess.Popen(self.command)

    @property
    def running(self) -> bool:
        """Whether the preview stitch is running in a subprocess."""
        with self._popen_lock:
            if self._popen_obj is None:
                return False
            if self._popen_obj.poll() is None:
                return True
            return False

    def wait(self):
        """Wait for this preview stitch to return."""
        if self.running:
            with self._popen_lock:
                self._popen_obj.wait()


class FinalStitcher(BaseStitcher):
    """A class to handle the final stich for a scan."""

    def __init__(
        self,
        images_dir,
        *,
        logger: lt.deps.InvocationLogger,
        overlap: Optional[float] = None,
        correlation_resize: Optional[float] = None,
        stitch_tiff: bool = False,
        scan_data_dict: Optional[dict[str, Any]] = None,
    ):
        """Initialise a final stitcher, this has more args than the base class.

        All args except images_dir are positional only.

        :param images_dir: The images directory of the scan to stitch.
        :param logger: The invocation logger for this stitch process.
        :param overlap: The scan overlap, if not known enter None. A value will be
            chosen from the scan_data_dict, or set to a default value if no value is
            available in the scan_data.
        :param correlation_resize: The fraction to resize images by when correlating,
            if not known enter None. A value will be chosen from the scan_data_dict, or
            set to a default value if no value is available in the scan_data.
        :param stitch_tiff: Whether to stitch a pyramidal TIFF.
        :param scan_data_dict: The ScanData for this scan as a dictionary. This is used
            to read/calculate overlap and correlation_resize if they are not provided.
        """
        self.logger = logger
        overlap, correlation_resize = self._process_inputs(
            overlap=overlap,
            correlation_resize=correlation_resize,
            scan_data_dict=scan_data_dict,
        )
        super().__init__(
            images_dir, overlap=overlap, correlation_resize=correlation_resize
        )
        self._mode = "all"

        tiff_arg = "--stitch_tiff" if stitch_tiff else "--no-stitch_tiff"
        self._extra_args = ["--stitch-dzi", tiff_arg]

    def _process_inputs(
        self,
        overlap: float,
        correlation_resize: float,
        scan_data_dict: Optional[dict[str, Any]],
    ) -> tuple[float, float]:
        """Process inputs to ensure ``overlap`` and ``correlation_resize`` have values.

        First the scan_data_dict is inspected for values to allow ``overlap`` and
        ``correlation_resize`` to be set correctly, if these values are not available
        then default values are used, and a warning is logged to the invocation logger.

        :param overlap: overlap as input to __init__
        :param correlation_resize: correlation_resize as input to __init__
        :param scan_data_dict: scan_data_dict as input to __init__

        :returns: overlap and correlation_resize as floats.
        """
        if overlap is None:
            if scan_data_dict is not None and "overlap" in scan_data_dict:
                overlap = scan_data_dict["overlap"]

            # Warn if still None and set to default.
            if overlap is None:
                overlap = DEFAULT_OVERLAP
                self.logger.warning(
                    "No value set for overlap. Attempting stitch with overlap "
                    f"value of {DEFAULT_OVERLAP}"
                )

        if correlation_resize is None:
            if scan_data_dict is not None:
                # Handle "capture resolution" being used to store the save resolution
                # in old scans.
                key = (
                    "capture resolution"
                    if "capture resolution" in scan_data_dict
                    else "save_resolution"
                )
                if key in scan_data_dict:
                    save_resolution = scan_data_dict[key]
                    correlation_resize = STITCHING_RESOLUTION[0] / save_resolution[0]
            # Warn if still None and set to default.
            if correlation_resize is None:
                correlation_resize = DEFAULT_RESIZE
                self.logger.warning(
                    "No information available to calculate stitch resize. Attempting "
                    f"stitch with resize value of {DEFAULT_RESIZE}"
                )
        return overlap, correlation_resize

    def start(
        self,
        cancel: lt.deps.CancelHook,
    ) -> None:
        """Run the final stitch logging any output.

        Raises:
            ChildProcessError if exit code is not zero
            InvocationCancelledError if the action is cancelled.

        """
        cmd = self.command
        self.logger.debug(f"Running command in subprocess: `{' '.join(cmd)}`")

        # Run the command piping stdout into the process for reading and
        # forwarding the stdrerr to stdout
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
        )
        # Stop opening pipe blocking writing to it
        os.set_blocking(process.stdout.fileno(), False)

        # TODO check if we still want this? Is it for debugging, or should it have
        # more explanation.
        self.logger.info(
            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
        )

        self._log_ongoing(process, cancel=cancel)

        if process.poll() == 0:
            self.logger.info("Stitching complete")
        else:
            raise ChildProcessError(f"Subprocess {cmd[0]} exited with an error.")

    def _log_ongoing(
        self,
        process: subprocess.Popen,
        cancel: lt.deps.CancelHook,
    ) -> None:
        """Log the ongoing process unless it is cancelled."""
        # Poll returns None while running, will return the error code when finished
        while process.poll() is None:
            self.log_buffer(process.stdout)
            # Once buffer is clear sleep for 0.2s before trying again.

            try:
                # Note that using cancel.sleep allows the InvocationCancelledError to
                # be thrown
                cancel.sleep(0.2)
            except lt.exceptions.InvocationCancelledError as e:
                self.logger.info("Stitching cancelled by user")
                process.kill()
                raise e

        # Print everything in the buffer when program finishes
        self.log_buffer(process.stdout)

    def log_buffer(self, buffer):
        # TODO work out type
        """Log everything in the buffer at INFO level."""
        while line := buffer.readline():
            self.logger.info(line)
