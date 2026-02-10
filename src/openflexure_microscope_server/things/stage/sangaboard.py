"""Provide a LabThings-FastAPI interface to the Sangaboard motor controller."""

from __future__ import annotations

import threading
import time
from collections.abc import Sequence
from contextlib import contextmanager
from copy import copy
from queue import Queue
from types import TracebackType
from typing import Any, Iterator, Literal, Optional, Self

import semver

import labthings_fastapi as lt
import sangaboard

from . import BaseStage

REQUIRED_VERSION = semver.Version.parse("1.0.0")
RECOMMENDED_VERSION = semver.Version.parse("1.0.4")


class JogCommand:
    """A base class for jog operations."""

    def __init__(self) -> None:
        """Initialise a JogCommand."""
        super().__init__()
        self.received = threading.Event()
        self.finished = threading.Event()


class JogMoveCommand(JogCommand):
    """A command to make a jog move."""

    def __init__(self, displacement: Sequence[int]) -> None:
        """Initialise a JogMoveCommand.

        :param displacement: The displacement for the jog move, in hardware coordinates.
        """
        super().__init__()
        self.displacement = displacement


class JogStopCommand(JogCommand):
    """A command to stop a jog move."""


class SangaboardThing(BaseStage):
    """A Thing to manage a Sangaboard motor controller.

    Internally, this uses the ``pysangaboard`` package from PyPi. This imports
    as ``sangaboard``. As ``pysangaboard`` does not support some features added
    to the Sangaboard firmware v1 (LED flashing, aborting moves, etc) this
    functionality is accessed by directly querying the serial interface.
    """

    def __init__(
        self,
        thing_server_interface: lt.ThingServerInterface,
        port: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialise SangaboardThing.

        Initialise the "Thing", but do not initialise an underlying
        ``Sangaboard`` object from ``pysangaboard`` until the Thing context
        manager is started.

        :param port: The serial port for the Sangaboard. Optional, this is used
            to stop the Sangaboard object querying available devices.
        :param ``**kwargs``: Any other keyword arguments to be passed to the
            Sangaboard class

        """
        self.sangaboard_kwargs = copy(kwargs)
        self.sangaboard_kwargs["port"] = port
        self._sangaboard_lock = threading.RLock()

        self._jog_lock = threading.Lock()
        self._jog_queue: Queue[JogCommand] = Queue[JogCommand](maxsize=1)
        self._jog_thread: Optional[threading.Thread] = None

        super().__init__(thing_server_interface, **kwargs)

    def __enter__(self) -> Self:
        """Connect to the sangaboard when the Thing context manager is opened."""
        self._sangaboard = sangaboard.Sangaboard(**self.sangaboard_kwargs)
        with self.sangaboard() as sb:
            sb.query("blocking_moves false")
        self.check_firmware()
        self.update_position()
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException],
        _exc_value: Optional[BaseException],
        _traceback: Optional[TracebackType],
    ) -> None:
        """Close the sangaboard connection when the Thing context manager is closed."""
        with self.sangaboard() as sb:
            sb.close()

    @contextmanager
    def sangaboard(self) -> Iterator[sangaboard.Sangaboard]:
        """Return the wrapped ``sangaboard.Sangaboard`` instance.

        This is protected by a ``threading.RLock``, which may change in future.
        """
        with self._sangaboard_lock:
            yield self._sangaboard

    axis_inverted: dict[str, bool] = lt.setting(
        default={"x": True, "y": False, "z": True}, readonly=True
    )
    """Used to convert coordinates between the program frame and the hardware frame."""

    def update_position(self) -> None:
        """Read position from the stage and set the corresponding property."""
        with self.sangaboard() as sb:
            self._hardware_position = dict(
                zip(self.axis_names, sb.position, strict=True)
            )

    def check_firmware(self) -> None:
        """Error/warn if firmware doesn't meet requirements/recommendations.

        Raise a Runtime Error if the version is below REQUIRED_VERSION

        Log a warning if the version is below RECOMMENDED_VERSION
        """
        with self.sangaboard() as sb:
            # This will raise a ValueError is if the firmware version cannot be parsed
            # this error will stop the microscope booting as we cannot ensure valid
            # firmware.
            version = semver.Version.parse(sb.firmware_version)

            # Raise an error if version is below required
            if version < REQUIRED_VERSION:
                raise RuntimeError(
                    f"Sangaboard firmware version {version} is below the required "
                    f"{REQUIRED_VERSION}."
                )

            # Warn if version is below recommended
            if version < RECOMMENDED_VERSION:
                self.logger.warning(
                    f"Sangaboard firmware version {version} is below the recommended "
                    f"{RECOMMENDED_VERSION}."
                )

    def _hardware_start_move_relative(self, displacement: Sequence[int]) -> None:
        """Start a relative move.

        This starts the stage moving, but does not wait for the move to complete. It
        sets ``self.moving`` to `True`: resetting it is the responsibility of the calling code.
        """
        with self.sangaboard() as sb:
            self.moving = True
            sb.move_rel(displacement)

    def _hardware_stop(self) -> None:
        """Stop any motion of the stage as soon as possible."""
        with self.sangaboard() as sb:
            sb.query("stop")
            self.moving = False

    def _move_duration(self, displacement: Sequence[int]) -> float:
        """Calculate the expected duration of a move with the given displacement."""
        max_displacement = max(abs(d) for d in displacement)
        return max_displacement * 0.001  # This does not yet check the board's speed.

    def _poll_moving(self) -> bool:
        """Determine if the stage is still moving.

        This also sets `self.moving` if the status has changed.

        :return: whether the stage is still moving.
        """
        with self.sangaboard() as sb:
            moving = sb.query("moving?") == "true"
            if self.moving != moving:
                self.moving = moving
            return moving

    def _poll_until_stopped(self) -> None:
        """Poll the stage until it reports that it has stopped moving."""
        with self.sangaboard():
            while self._poll_moving():
                lt.cancellable_sleep(0.1)

    def _hardware_move_relative(
        self,
        block_cancellation: bool = False,
        **kwargs: int,
    ) -> None:
        """Make a relative move in the coordinate system used by the sangaboard."""
        displacement = [kwargs.get(axis, 0) for axis in self.axis_names]
        duration = self._move_duration(displacement)
        with self.sangaboard() as sb:
            try:
                sb.move_rel(displacement)
                if block_cancellation:
                    sb.query("notify_on_stop")
                else:
                    if duration > 0.2:
                        lt.cancellable_sleep(
                            duration - 0.1
                        )  # Avoid unnecessary polling
                    while sb.query("moving?") == "true":
                        lt.cancellable_sleep(0.1)
            except lt.exceptions.InvocationCancelledError as e:
                # If the move has been cancelled, stop it but don't handle the exception.
                # We need the exception to propagate in order to stop any calling tasks,
                # and to mark the invocation as "cancelled" rather than stopped.
                self._hardware_stop()
                raise e
            finally:
                self.moving = False
                self.update_position()

    def _hardware_move_absolute(
        self,
        block_cancellation: bool = False,
        **kwargs: int,
    ) -> None:
        """Make a absolute move in the coordinate system used by the sangaboard."""
        with self.sangaboard():
            self.update_position()
            displacement = {
                axis: int(pos) - self._hardware_position[axis]
                for axis, pos in kwargs.items()
                if axis in self.axis_names
            }
            self._hardware_move_relative(
                block_cancellation=block_cancellation, **displacement
            )

    @lt.action
    def set_zero_position(self) -> None:
        """Make the current position zero in all axes.

        This action does not move the stage, but resets the position to zero.
        It is intended for use after manually or automatically recentring the
        stage.
        """
        with self.sangaboard() as sb:
            sb.zero_position()
        self.update_position()

    def set_led(
        self,
        led_on: bool = True,
        led_channel: Literal["cc"] = "cc",
    ) -> None:
        """Flash the LED to identify the board.

        This is intended to be useful in situations where there are multiple
        Sangaboards in use, and it is necessary to identify which one is
        being addressed.
        """
        led_command = f"led_{led_channel}"
        with self.sangaboard() as sb:
            return_value = sb.query(f"{led_command}?")
            if not return_value.startswith("CC LED:"):
                raise IOError("The sangaboard does not support LED control")

            # Reading and setting LED brightness suffers from repeated reads and writes
            # decreasing the value. Rather than use the value the code warns that the value
            # cannot be used.
            if led_on:
                on_brightness = 0.32
                sb.query(f"{led_command} {on_brightness}")
            else:
                sb.query(f"{led_command} 0")

    @lt.action
    def jog(self, stop: bool = False, **kwargs: int) -> None:
        r"""Make a relative move that may be interrupted by a future ``jog``\ .

        This action makes a relative move. If another ``jog`` action is called while
        a ``jog`` is already in progress, the first will be stopped and the second
        will start immediately. This allows for responsive manual control of the
        stage, for example with a joystick.

        :param stop: if this is set to `True` the jog will be terminated.
        :param \**kwargs: Keyword arguments should be axis names.
        """
        if stop:
            self._send_jog_command(JogStopCommand(), wait=True, timeout=1)
        else:
            self._hardware_jog(**self._apply_axis_direction(kwargs))

    def _hardware_jog(self, **kwargs: int) -> None:
        r"""Make a relative move that may be interrupted by a future ``jog``\ .

        This function uses hardware coordinates, ``jog`` is the public wrapper that
        applies any neecessary transform and then calls this function. See the
        docs for that function for more explanation.

        See `_jog_loop` for an explanation of the mechanism.

        :param \**kwargs: Keyword arguments should be axis names.
        """
        move = [kwargs.get(axis, 0) for axis in self.axis_names]
        self._send_jog_command(
            JogMoveCommand(move),
            timeout=self._move_duration(move) + 1,
        )

    def _send_jog_command(
        self, command: JogCommand, timeout: Optional[float] = None
    ) -> None:
        """Send a jog command to the background jog thread.

        This function will start the background thread if it is not running.
        This function acquires `_jog_lock` and uses the `_jog_send` event to signal
        the thread to read the next command. As commands interrupt each other, this
        function should never block for a long time.

        :param command: the jog command to send.
        :param timeout: how long to wait for the command to be completed, or `None`
            to skip waiting.
        """
        with self._jog_lock:
            # Make sure the queue exists.
            # Check the background thread is running, and restart it if not.
            if self._jog_thread is None or not self._jog_thread.is_alive():
                self._jog_queue = Queue[JogCommand](maxsize=1)
                self._jog_thread = threading.Thread(target=self._jog_loop)
                self._jog_thread.start()
            self._jog_queue.put(command)
            command.received.wait(1)
            if timeout is not None:
                command.finished.wait(timeout)

    def _jog_loop(self) -> None:
        r"""Execute jog commands in a background thread.

        This function is intended to be run in a background thread. It will look at
        `self._jog_command` when the `self._jog_send` event is set, and signal that
        the command is being processed with `self._jog_received`\ .

        If no new command is received before the current command finishes, the thread
        will terminate, and `self._jog_received` will be set again. This means that
        it should be safe to
        """
        duration = 1  # How long to wait initially. This shouldn't ever need to be long.
        # On subsequent loop iterations, we'll wait long enough that we expect the last
        # move to have finished.
        previous_command: Optional[JogCommand] = None
        with (
            self.sangaboard() as _sb
        ):  # prevent others using the sangaboard while jogging.
            while True:
                try:
                    command = self._jog_queue.get(timeout=duration)
                except TimeoutError:
                    if self._poll_moving():
                        # If there's no new command, keep checking for new commands until
                        # we stop.
                        duration = 0.1
                        continue
                    # Once the stage is no longer moving, stop listening for commands.
                    break
                command.received.set()  # Acknowledge the command
                if previous_command:
                    previous_command.finished.set()  # Notify the last command it's superseded
                if isinstance(command, JogMoveCommand):
                    self._hardware_start_move_relative(command.displacement)
                    duration = self._move_duration(command.displacement)
                elif isinstance(command, JogStopCommand):
                    self._hardware_stop()
                    self._poll_until_stopped()
                    duration = 0.1  # Next iteration, we will probably time out.
                else:
                    raise RuntimeError(f"Unknown jog command: {command}")
            if previous_command:
                # Notify the last command that it finished, because we stopped moving.
                previous_command.finished.set()
