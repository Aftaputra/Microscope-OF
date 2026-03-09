"""Communicate with OpenFlexure Stitching to perform stitches for scans.

This includes both live stitching and final stitching. This is done via subprocess
to call openflexure-stitching over CLI. This cannot be done via Threading due to the
CPU intensity of stitching causing scanning problems due to the Python Global
Interpreter Lock (GIL). May be possible to shift to multiprocessing in the future.
"""

import logging
import os
import shlex
import signal
import subprocess
import threading
from typing import IO, Optional

from pydantic import BaseModel

import labthings_fastapi as lt

from openflexure_microscope_server.utilities import is_path_safe

IS_WINDOWS = os.name == "nt"

STITCHING_CMD = "openflexure-stitch"
STITCHING_RESOLUTION = (820, 616)
STITCH_TILE_SIZE = 8192

DEFAULT_OVERLAP = 0.1
DEFAULT_RESIZE = 0.5

# A list of commands that are forbidden in any part of a generated CLI command.
# This provides defense-in-depth against trying to execute arbitrary shells
# or elevation tools.
FORBIDDEN_COMMANDS = {
    "sudo",
    "sh",
    "bash",
    "perl",
    "ruby",
    "php",
    "nc",
    "netcat",
    "curl",
    "wget",
}


class StitchingSettings(BaseModel):
    """The data needed to stitch a scan."""

    correlation_resize: float
    """The resize factor applied to images when the stitching program is correlating."""

    overlap: float
    """The overlap between adjacent images as a fraction of the image size."""


class ExternalSigkillError(ChildProcessError):
    """Exception called when stitch is killed by an external process calling Sigkill."""


class StitcherValidationError(RuntimeError):
    """The stitcher received values that it deems unsafe to create a command from."""


def validate_command(cmd: list[str]) -> None:
    """Validate that the command only contains characters that are allowed in a path.

    The values in the commands should be numbers, commandline flags, paths, and
    executables. All of these should be allowed by ``is_path_safe``.

    This also checks against a blacklist of forbidden commands for defense-in-depth.

    :raises StitcherValidationError: if any element in the command is not safe.
    """
    for element in cmd:
        # Check against forbidden commands (case-insensitive)
        if element.lower() in FORBIDDEN_COMMANDS:
            raise StitcherValidationError(
                f"Invalid stitching command: Forbidden element '{element}' detected."
            )

        # Ensure characters are safe for a path component
        if not is_path_safe(element):
            raise StitcherValidationError(
                f"Invalid stitching command: Element '{element}' contains unsafe characters."
            )


class BaseStitcher:
    """A base stitching class for all stitchers. Don't initialise this directly.

    The base class has no way to run the command. Child classes should either implement
    ``start``, ``running``, and ``wait`` methods if return after starting the
    subprocess and can be polled or waited on like a thread; or ``run`` if the
    the function blocks while the stitching subprocess is ongoing and return once
    complete.
    """

    def __init__(
        self, images_dir: str, *, overlap: float, correlation_resize: float
    ) -> None:
        """Initialise a stitcher.

        All args except images_dir are positional only.

        :param images_dir: The images directory of the scan to stitch.
        :param overlap: The scan overlap.
        :param correlation_resize: The fraction to resize images by when correlating.
        """
        # Set minimum overlap to 90% of the scan overlap to catch only images
        # directly adjacent, not images with overlapping corners.
        self.images_dir = images_dir
        try:
            overlap = float(overlap)
            correlation_resize = float(correlation_resize)
        except ValueError as e:
            raise StitcherValidationError(
                "Stitching inputs overlap or correlation_resize were not floats as "
                "expected."
            ) from e
        self.validate_path()

        self.min_overlap = round(overlap * 0.9, 2)
        self.correlation_resize = float(correlation_resize)
        self._mode = "all"
        self._extra_args: list[str] = []

    @property
    def command(self) -> list[str]:
        """The command to run with subprocess.Popen."""
        # Revalidate for good measure,
        self.validate_path()

        # The command, and the mode
        base_args = shlex.split(STITCHING_CMD, posix=not IS_WINDOWS)
        initial_args = base_args + ["--stitching_mode", self._mode]
        # Use float() just to really ensure that anything input is a float
        setting_args = [
            "--minimum_overlap",
            f"{float(self.min_overlap)}",
            "--resize",
            f"{float(self.correlation_resize)}",
        ]
        full_cmd = initial_args + self._extra_args + setting_args + [self.images_dir]
        validate_command(full_cmd)
        return full_cmd

    def validate_path(self) -> None:
        """Check path is safe before making a command to run with subprocess.

        This is essential for stopping arbitrary code execution.

        :raises RuntimeError: if inputs are unsafe.
        """
        if not is_path_safe(self.images_dir):
            raise StitcherValidationError(
                "Invalid directory path: Contains unsafe characters."
            )


class PreviewStitcher(BaseStitcher):
    """A stitcher for stitching an ongoing scan in preview mode.

    Use ``start()`` to start a scan, and ``running`` to check if it is complete, or
    ``wait()`` to wait for it to complete.

    The same stitcher object can be run multiple times to update the preview. However,
    one preview must finish before another can be started.
    """

    def __init__(
        self, images_dir: str, *, overlap: float, correlation_resize: float
    ) -> None:
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
            return self._popen_obj.poll() is None

    def wait(self) -> None:
        """Wait for this preview stitch to return.

        :raises InvocationCancelledError: if the action is cancelled.
        """
        while self.running:
            try:
                # This should act exactly like sleep if not started in a LabThings
                # action thread. In an action thread it will raise
                # InvocationCancelledError if the action is cancelled.
                lt.cancellable_sleep(0.2)
            except lt.exceptions.InvocationCancelledError as e:
                with self._popen_lock:
                    if self._popen_obj is not None:
                        if IS_WINDOWS:
                            # Windows has no SIGKILL
                            self._popen_obj.kill()
                        else:
                            self._popen_obj.send_signal(signal.SIGKILL)
                raise (e)


class FinalStitcher(BaseStitcher):
    """A class to handle the final stitch for a scan."""

    def __init__(
        self,
        images_dir: str,
        *,
        logger: logging.Logger,
        stitching_settings: StitchingSettings,
        stitch_tiff: bool = False,
    ) -> None:
        """Initialise a final stitcher, this has more args than the base class.

        All args except images_dir are positional only.

        :param images_dir: The images directory of the scan to stitch.
        :param logger: The logger from the Thing that created this stitcher.
        :param stitching_settings: A StitchingSettings model this can be loaded from a
            HistoricScanData for this scan as a dictionary.
        :param stitch_tiff: Whether to stitch a pyramidal TIFF.
        """
        if not isinstance(stitching_settings, StitchingSettings):
            raise StitcherValidationError(
                "Final stitcher requires settings to be set as a StitchingSettings "
                "model"
            )
        self.logger = logger
        overlap = stitching_settings.overlap
        correlation_resize = stitching_settings.correlation_resize
        super().__init__(
            images_dir, overlap=overlap, correlation_resize=correlation_resize
        )
        self._mode = "all"

        tiff_arg = "--stitch_tiff" if stitch_tiff else "--no-stitch_tiff"
        self._extra_args = [
            "--stitch_dzi",
            tiff_arg,
            "--tile_size",
            str(STITCH_TILE_SIZE),
        ]

    def run(self) -> None:
        """Run the final stitch logging any output.

        :raises ChildProcessError: if exit code is not zero
        :raises InvocationCancelledError: if the action is cancelled.
        """
        cmd = self.command
        self.logger.debug(f"Running command in subprocess: `{' '.join(cmd)}`")

        # Run the command piping stdout into the process for reading and
        # forwarding the stdrerr to stdout
        process: subprocess.Popen[str] = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            text=True,
        )
        if process.stdout is None:  # pragma: no cover - impossible with stdout=PIPE
            raise RuntimeError("stdout pipe was not created")
        # Stop opening pipe blocking writing to it
        os.set_blocking(process.stdout.fileno(), False)
        output_lines = self._log_ongoing(process)
        returncode = process.wait()
        full_output = "\n".join(output_lines)

        if returncode == 0:
            self.logger.info("Stitching complete")

        elif returncode == -9:
            raise ExternalSigkillError(
                "Stitching was killed by an external process. "
                "Most likely due to running out of memory."
            )

        elif returncode == 1:
            if "No space left on device" in full_output or "Errno 28" in full_output:
                raise ChildProcessError(
                    "Not enough space on disk to stitch. Please delete some scans or increase "
                    "your storage size."
                )
            if (
                "Maximum supported image dimension" in full_output
                or "OSError: broken data stream when writing image file" in full_output
            ):
                raise ChildProcessError(
                    "Image dimensions too big for stitching into a JPEG file. Stitched output will "
                    "exceed the maximum number of pixels in a JPEG (65,535x65,535 pixels). Download "
                    "the full scan and stitch with alternate settings."
                )
            raise ChildProcessError(
                "Unexpected error when stitching (Exit code 1).\nCheck the logs for more information."
            )
        else:
            raise ChildProcessError(
                f"Stitching errored with exit code {returncode}.\nCheck the logs for more information."
            )

    def _log_ongoing(self, process: subprocess.Popen[str]) -> list[str]:
        """Log the ongoing process unless it is cancelled.

        :returns: a list of all lines
        """
        if process.stdout is None:  # pragma: no cover - impossible with stdout=PIPE
            raise RuntimeError("stdout pipe was not created")

        output_lines: list[str] = []
        # Poll returns None while running, will return the error code when finished
        while process.poll() is None:
            output_lines.extend(self.log_buffer(process.stdout))

            try:
                # This should act exactly like sleep if not started in a LabThings
                # action thread. In an action thread it will raise
                # InvocationCancelledError if the action is cancelled.
                lt.cancellable_sleep(0.2)
            except lt.exceptions.InvocationCancelledError as e:
                self.logger.info("Stitching cancelled by user")
                process.kill()
                raise e

        # Print everything in the buffer when program finishes
        output_lines.extend(self.log_buffer(process.stdout))

        return output_lines

    def log_buffer(self, buffer: IO[str]) -> list[str]:
        """Log everything currently available in the buffer and return lines."""
        lines: list[str] = []

        while line := buffer.readline():
            clean = line.rstrip()
            self.logger.info(clean)
            lines.append(line)

        return lines
