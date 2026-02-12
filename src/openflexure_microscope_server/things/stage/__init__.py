"""A package for stage control Things.

`BaseStage` is the base class that provides core stage functionality, but
no hardware interface control. To create a stage Thing to control a specific
piece of hardware the BaseStage should be subclassed, and any method raising
a NotImplementedError should be created.

As the object will be used as a context manager create the hardware connection in
``__enter__`` (not in ``__init__``), and close the connection with ``__exit__``.
"""

from __future__ import annotations

import queue
import threading
from collections.abc import Mapping, Sequence
from typing import Any, Literal, Optional, overload

import labthings_fastapi as lt


class RedefinedBaseMovementError(RuntimeError):
    """The subclass of BaseStage has overridden ``move_relative`` or ``move_absolute``.

    Overriding ``move_relative`` or ``move_absolute`` can be problematic as these use the
    external position not the hardware position. It is recommended to override
    ``_hardware_move_relative`` and ``_hardware_move_absolute`` instead.

    The BaseStage will raise this on ``__init__``, it is the last thing ``__init__``
    does. As such, this exception can be captured by ``try`` if a stage needs to
    override these for a specific reason.
    """


class JogCommand:
    """A base class for jog operations."""

    def __init__(self) -> None:
        """Initialise a JogCommand."""
        super().__init__()
        self.received = threading.Event()
        self.finished = threading.Event()

    def __repr__(self) -> str:
        """Represent the command as a string."""
        return f"<{self.__class__.__name__}>"


class JogMoveCommand(JogCommand):
    """A command to make a jog move."""

    def __init__(self, displacement: Sequence[int]) -> None:
        """Initialise a JogMoveCommand.

        :param displacement: The displacement for the jog move, in hardware coordinates.
        """
        super().__init__()
        self.displacement = displacement

    def __repr__(self) -> str:
        """Represent the command as a string."""
        return f"<{self.__class__.__name__} {self.displacement}>"


class JogStopCommand(JogCommand):
    """A command to stop a jog move."""


class BaseStage(lt.Thing):
    """A base stage class for OpenFlexure translation stages.

    This can't be used directly but should reduce boilerplate code when
    implementing new stages.

    Note that the coordinate system used for the microscope may need to have different
    axis direction as those used by the underlying stage controller.

    A minimal working stage must implement ``_hardware_move_relative``
    and ``_hardware_move_absolute`` actions, which update the ``_hardware_position``
    attribute on completion, and also should implement ``set_zero_position``.
    """

    _axis_names = ("x", "y", "z")

    def __init__(self, thing_server_interface: lt.ThingServerInterface) -> None:
        """Initialise the stage.

        :raises RedefinedBaseMovementError: if ``move_relative`` and/or
            ``move_absolute`` are overridden. It is recommended to override
            ``_hardware_move_relative`` and/or ``_hardware_move_absolute`` instead so
            that all code in the child class uses the hardware reference frame.
        """
        super().__init__(thing_server_interface)
        self._hardware_lock = threading.RLock()
        self._jog_lock = threading.Lock()
        self._jog_queue: queue.Queue[JogCommand] = queue.Queue[JogCommand](maxsize=1)
        self._jog_thread: Optional[threading.Thread] = None
        self._hardware_position = dict.fromkeys(self._axis_names, 0)

        # This must be the last thing the function does in case it is caught in a try.
        if (
            self.__class__.move_relative.func is not BaseStage.move_relative.func
            or self.__class__.move_absolute.func is not BaseStage.move_absolute.func
        ):
            raise RedefinedBaseMovementError(
                "move_relative and/or move_absolute has been overridden. This may "
                "cause issues as the base methods implement converting from program "
                "coordinates to hardware coordinates. Consider overriding "
                "_hardware_move_relative and/or _hardware_move_absolute instead."
            )

    @lt.property
    def axis_names(self) -> Sequence[str]:
        """The names of the stage's axes, in order."""
        return self._axis_names

    @lt.property
    def position(self) -> Mapping[str, int]:
        """Current position of the stage."""
        return self._apply_axis_direction(self._hardware_position)

    moving: bool = lt.property(default=False, readonly=True)
    """Whether the stage is in motion."""

    axis_inverted: dict[str, bool] = lt.setting(
        default={"x": False, "y": False, "z": False}, readonly=True
    )
    """Used to convert coordinates between the program frame and the hardware frame."""

    def update_position(self) -> None:
        """Read position from the stage and set the corresponding property."""
        raise NotImplementedError(
            "StageThings must define their own update_position method"
        )

    @overload
    def _apply_axis_direction(self, position: list[int] | tuple[int]) -> list[int]: ...

    @overload
    def _apply_axis_direction(
        self, position: Mapping[str, int]
    ) -> Mapping[str, int]: ...

    def _apply_axis_direction(
        self, position: list[int] | tuple[int] | Mapping[str, int]
    ) -> list[int] | Mapping[str, int]:
        if isinstance(position, (list, tuple)):
            return [
                -int(pos) if inverted else int(pos)
                for pos, inverted in zip(
                    position, self.axis_inverted.values(), strict=True
                )
            ]
        if isinstance(position, Mapping):
            try:
                return {
                    ax: -int(position[ax])
                    if self.axis_inverted[ax]
                    else int(position[ax])
                    for ax in position
                }
            except KeyError as e:
                raise KeyError(
                    f"One or more axis in {position.keys()} is not defined."
                ) from e
        raise TypeError(
            "Position must be a sequence of positions or a mapping from axis to position."
        )

    @property
    def thing_state(self) -> Mapping[str, Any]:
        """Summary metadata describing the current state of the stage."""
        return {"position": self.position}

    @lt.action
    def invert_axis_direction(self, axis: Literal["x", "y", "z"]) -> None:
        """Invert the direction setting of the given axis.

        :param axis: The axis name (x, y or z) to invert.
        """
        # Not mutating in place so that setting is saved on change.
        direction = self.axis_inverted
        try:
            direction[axis] = not direction[axis]
        except KeyError as e:
            raise KeyError(f"The axis {axis} is not defined.") from e
        self.axis_inverted = direction

    @lt.action
    def move_relative(self, block_cancellation: bool = False, **kwargs: int) -> None:
        """Make a relative move. Keyword arguments should be axis names."""
        self._hardware_move_relative(
            block_cancellation=block_cancellation,
            **self._apply_axis_direction(kwargs),
        )

    def _hardware_move_relative(
        self, block_cancellation: bool = False, **kwargs: int
    ) -> None:
        """Make a relative move in the coordinate system used by the physical hardware.

        Make sure to use and update ``self._hardware_position`` not ``self.position``.
        """
        raise NotImplementedError(
            "StageThings must define their own _hardware_move_relative method"
        )

    @lt.action
    def move_absolute(self, block_cancellation: bool = False, **kwargs: int) -> None:
        """Make an absolute move. Keyword arguments should be axis names."""
        self._hardware_move_absolute(
            block_cancellation=block_cancellation,
            **self._apply_axis_direction(kwargs),
        )

    def _hardware_move_absolute(
        self,
        block_cancellation: bool = False,
        **kwargs: int,
    ) -> None:
        """Make a absolute move in the coordinate system used by the physical hardware.

        Make sure to use and update ``self._hardware_position`` not ``self.position``.
        """
        raise NotImplementedError(
            "StageThings must define their own move_absolute method"
        )

    def _hardware_start_move_relative(self, displacement: Sequence[int]) -> None:
        """Start a relative move."""
        raise NotImplementedError(
            "StageThings must define their own hardware_start_move_relative method"
        )

    def _hardware_stop(self) -> None:
        raise NotImplementedError(
            "StageThings must define their own _hardware_stop method"
        )

    def _poll_moving(self) -> bool:
        """Determine if the stage is still moving."""
        raise NotImplementedError(
            "StageThings must define their own _poll_moving method"
        )

    def _estimate_move_duration(self, displacement: Sequence[int]) -> float:
        """Calculate the expected duration of a move with the given displacement."""
        max_displacement = max(abs(d) for d in displacement)
        return max_displacement * 0.001  # This does not yet check the board's speed.

    @lt.action
    def jog(self, stop: bool = False, **kwargs: int) -> None:
        """Make a relative move that may be interrupted by a future ``jog``.

        This action makes a relative move. If another ``jog`` action is called while
        a ``jog`` is already in progress, the first will be stopped and the second
        will start immediately. This allows for responsive manual control of the
        stage, for example with a joystick.

        :param stop: if this is set to ``True`` the jog will be terminated.
        :param kwargs: Keyword arguments should be axis names.
        """
        if stop:
            self._send_jog_command(JogStopCommand(), timeout=1)
        else:
            self._hardware_jog(**self._apply_axis_direction(kwargs))

    def _hardware_jog(self, **kwargs: int) -> None:
        """Make a relative move that may be interrupted by a future ``jog``.

        This function uses hardware coordinates, ``jog`` is the public wrapper that
        applies any neecessary transform and then calls this function. See the
        docs for that function for more explanation.

        See `_jog_loop` for an explanation of the mechanism.

        :param kwargs: Keyword arguments should be axis names.
        """
        move = [kwargs.get(axis, 0) for axis in self.axis_names]
        self._send_jog_command(
            JogMoveCommand(move),
            timeout=self._estimate_move_duration(move) + 1,
        )

    def _send_jog_command(
        self, command: JogCommand, timeout: Optional[float] = None
    ) -> None:
        """Send a jog command to the background jog thread.

        This function will start the background thread if it is not running.
        This function acquires ``_jog_lock`` and uses the ``_jog_send`` event to signal
        the thread to read the next command. As commands interrupt each other, this
        function should never block for a long time.

        :param command: the jog command to send.
        :param timeout: how long to wait for the command to be completed, or ``None``
            to skip waiting.
        """
        if not self._jog_lock.acquire(timeout=0.1):
            self.logger.warning(
                "Could not send a jog message, this indicates a lock error."
            )
            return
        try:
            # Make sure the queue exists.
            # Check the background thread is running, and restart it if not.
            if self._jog_thread is None or not self._jog_thread.is_alive():
                self.logger.info("Starting background thread for jog commands")
                self._jog_queue = queue.Queue[JogCommand](maxsize=1)
                self._jog_thread = threading.Thread(
                    target=self._jog_loop, args=(command,)
                )
                self._jog_thread.start()
            else:
                self._jog_queue.put(command)
            command.received.wait(1)
        finally:
            self._jog_lock.release()
        # The final wait happens after releasing the lock: this allows jog moves to
        # be interrupted.
        if timeout is not None:
            command.finished.wait(timeout)

    def _jog_loop(self, first_command: JogCommand) -> None:
        """Execute jog commands in a background thread.

        This function is intended to be run in a background thread. It will look at
        ``self._jog_command`` when the ``self._jog_send`` event is set, and signal that
        the command is being processed with ``self._jog_received``.

        If no new command is received before the current command finishes, the thread
        will terminate, and ``self._jog_received`` will be set again. This means that
        it should be safe to
        """
        # Timeout for checking queue
        timeout = 0.1
        previous_command: Optional[JogCommand] = None
        command: Optional[JogCommand] = first_command

        # prevent others using the stage while jogging.
        with self._hardware_lock:
            while command is not None:
                # Acknowledge the command
                command.received.set()
                if previous_command:
                    # Notify the last command it's superseded
                    previous_command.finished.set()
                previous_command = command
                if isinstance(command, JogMoveCommand):
                    self._hardware_start_move_relative(command.displacement)
                    timeout = self._estimate_move_duration(command.displacement)
                elif isinstance(command, JogStopCommand):
                    self._hardware_stop()
                    # Next iteration, we will probably time out.
                    timeout = 0.1
                else:
                    raise RuntimeError(f"Unknown jog command: {command}")
                self.update_position()
                command = self._get_from_jog_queue(timeout)

    def _get_from_jog_queue(self, timeout: float) -> Optional[JogCommand]:
        """Get the next JogCommand from the jog queue.

        :param timeout: The estimtated time the move will take for the queue timeout.
        :return: The jog command or None if the stage stops before a command is
            received.
        """
        while True:
            try:
                return self._jog_queue.get(timeout=timeout)
            except queue.Empty:
                if not self._poll_moving():
                    # The stage is no longer moving, return None
                    return None
            # If we reached here then the stage is still moving shorten timeout and
            # check again.
            timeout = 0.1

    @lt.action
    def set_zero_position(self) -> None:
        """Make the current position zero in all axes.

        This action does not move the stage, but resets the position to zero.
        It is intended for use after manually or automatically recentring the
        stage.
        """
        raise NotImplementedError(
            "StageThings must define their own set_zero_position method"
        )

    @lt.action
    def get_xyz_position(self) -> tuple[int, int, int]:
        """Return a tuple containing (x, y, z) position.

        :raises KeyError: if this stage does not have axes named "x", "y", and "z".

        This method provides the interface expected by the camera_stage_mapping.
        """
        position_dict = self.position
        return (position_dict["x"], position_dict["y"], position_dict["z"])

    @lt.action
    def move_to_xyz_position(self, xyz_pos: tuple[int, int, int]) -> None:
        """Move to the location specified by an (x, y, z) tuple.

        :param xyz_pos: The (x, y, z) position to move to.

        :raises KeyError: if this stage does not have axes named "x", "y", and "z".

        This method provides the interface expected by the camera_stage_mapping.
        """
        self.move_absolute(x=xyz_pos[0], y=xyz_pos[1], z=xyz_pos[2])
