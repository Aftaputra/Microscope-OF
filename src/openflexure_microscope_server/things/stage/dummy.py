"""Functionality for mimicking a stage during simulation and testing."""

from __future__ import annotations

import threading
import time
from collections.abc import Sequence
from types import TracebackType
from typing import Any, Mapping, Optional, Self

import labthings_fastapi as lt

from . import BaseStage


class DummyStage(BaseStage):
    """A dummy stage for testing purposes.

    This stage should work similarly to a Sangaboard stage, but without any
    hardware attached.
    """

    def __init__(
        self,
        thing_server_interface: lt.ThingServerInterface,
        step_time: float = 0.001,
        **kwargs: Any,
    ) -> None:
        """Initialise the Dummy stage, setting the step_time to adjust the speed.

        :param step_time: The time in seconds per "motor" step. The default of 0.001
            works well for the live simulation. For unit testing it is very slow
            so the speed can be increased. Increasing it too far is problematic if
            also doing computationally heavy tasks like simulated image blurring.
        """
        super().__init__(thing_server_interface, **kwargs)
        self._move_thread: Optional[threading.Thread] = None
        self.step_time = step_time
        self.instantaneous_position: Mapping[str, int] = self._hardware_position
        self._inst_pos_lock = threading.Lock()
        self._abort_move = threading.Event()

    def __enter__(self) -> Self:
        """Register the stage position when the Thing context manager is opened."""
        self.instantaneous_position = self._hardware_position
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException],
        _exc_value: Optional[BaseException],
        _traceback: Optional[TracebackType],
    ) -> None:
        """Nothing to do when the Thing context manager is closed."""

    axis_inverted: dict[str, bool] = lt.setting(
        default={"x": True, "y": False, "z": False}, readonly=True
    )
    """Used to convert coordinates between the program frame and the hardware frame."""

    def update_position(self) -> None:
        """Read position from the stage and set the corresponding property."""
        pass

    def _calc_fractional_pos(
        self, displacement: Sequence[int], fraction_complete: float
    ) -> dict[str, int]:
        """Calculate the position a fraction through a move."""
        return {
            ax: self._hardware_position[ax] + int(fraction_complete * disp)
            for ax, disp in zip(self.axis_names, displacement, strict=True)
        }

    def _apply_move(self, displacement: Sequence[int]) -> None:
        """Make a move, this function is designed to be run in a thread by jogging.

        This can't be used for normal movements as the delays setting up the extra
        threads causes autofucs to fail. As such `_hardware_move_relative` is similarly
        structured.

        Interrupt this function with the ``self._abort_move`` event.

        :param displacement: The (x, y, z) position.
        """
        try:
            fraction_complete = 0.0
            dt = self.step_time
            max_displacement = max(abs(v) for v in displacement)
            start_time = time.time()
            while time.time() - start_time < dt * max_displacement:
                if self._abort_move.is_set():
                    break
                fraction_complete = (time.time() - start_time) / (dt * max_displacement)
                self.instantaneous_position = self._calc_fractional_pos(
                    displacement, fraction_complete
                )
            if not self._abort_move.is_set():
                fraction_complete = 1.0
        finally:
            self._hardware_position = self._calc_fractional_pos(
                displacement, fraction_complete
            )
            self.instantaneous_position = self._hardware_position

    def _hardware_start_move_relative(self, displacement: Sequence[int]) -> None:
        """Start a relative move.

        This starts the stage moving, but does not wait for the move to complete. It
        sets ``self.moving`` to ``True``: resetting it is the responsibility of the
        calling code.
        """
        with self._hardware_lock:
            self.moving = True
            self._abort_move.clear()
            self._move_thread = threading.Thread(
                target=self._apply_move, args=(displacement,)
            )
            self._move_thread.start()

    def _hardware_stop(self) -> None:
        with self._hardware_lock:
            self._abort_move.set()
            self.moving = False

    def _poll_moving(self) -> bool:
        """Determine if the stage is still moving."""
        if self._move_thread is None:
            return False
        moving = self._move_thread.is_alive()
        if self.moving != moving:
            self.moving = moving
        return moving

    def _hardware_move_relative(
        self,
        block_cancellation: bool = False,
        **kwargs: int,
    ) -> None:
        """Make a relative move. Keyword arguments should be axis names."""
        with self._hardware_lock:
            displacement = [kwargs.get(k, 0) for k in self.axis_names]
            self.moving = True
            # This follows a similar structure to _apply_move but need a different
            # breakning mechanism. Running apply move in a thread and breaking here
            # results in significantly worse autofocus
            try:
                fraction_complete = 0.0
                dt = self.step_time
                max_displacement = max(abs(v) for v in displacement)
                start_time = time.time()
                while time.time() - start_time < dt * max_displacement:
                    if block_cancellation:
                        time.sleep(self.step_time)
                    else:
                        lt.cancellable_sleep(self.step_time)
                    fraction_complete = (time.time() - start_time) / (
                        dt * max_displacement
                    )
                    self.instantaneous_position = self._calc_fractional_pos(
                        displacement, fraction_complete
                    )
                fraction_complete = 1.0
            except lt.exceptions.InvocationCancelledError as e:
                # If the move has been cancelled, stop it but don't handle the
                # exception. We need the exception to propagate in order to stop
                # any calling tasks, and to mark the invocation as "cancelled"
                # rather than stopped.
                raise e
            finally:
                self._hardware_position = self._calc_fractional_pos(
                    displacement, fraction_complete
                )
                self.instantaneous_position = self._hardware_position
                self.moving = False

    def _hardware_move_absolute(
        self,
        block_cancellation: bool = False,
        **kwargs: int,
    ) -> None:
        """Make an absolute move. Keyword arguments should be axis names."""
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
        with self._hardware_lock:
            self._hardware_position = dict.fromkeys(self.axis_names, 0)
            self.instantaneous_position = self._hardware_position
