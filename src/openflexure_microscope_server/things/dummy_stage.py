from __future__ import annotations
from labthings_fastapi.descriptors.property import PropertyDescriptor
from labthings_fastapi.thing import Thing
from labthings_fastapi.decorators import thing_action, thing_property
from labthings_fastapi.dependencies.invocation import CancelHook, InvocationCancelledError
from collections.abc import Sequence, Mapping
import time


class DummyStage(Thing):
    """A dummy stage for testing purposes
    
    This stage should work similarly to a Sangaboard stage, but without any
    hardware attached.
    """
    _axis_names = ("x", "y", "z")

    def __enter__(self):
        pass

    def __exit__(self, _exc_type, _exc_value, _traceback):
        pass

    @thing_property
    def axis_names(self) -> Sequence[str]:
        """The names of the stage's axes, in order."""
        return self._axis_names

    position = PropertyDescriptor(
        Mapping[str, int],
        {k: 0 for k in _axis_names},
        description="Current position of the stage",
        readonly=True,
        observable=True,
    )

    moving = PropertyDescriptor(
        bool,
        False,
        description="Whether the stage is in motion",
        readonly=True,
        observable=True,
    )

    @property
    def thing_state(self):
        """Summary metadata describing the current state of the stage"""
        return {
            "position": self.position
        }
    
    @thing_action
    def move_relative(self, cancel: CancelHook, block_cancellation: bool=False, **kwargs: Mapping[str, int]):
        """Make a relative move. Keyword arguments should be axis names."""
        displacement = [kwargs.get(k, 0) for k in self.axis_names]
        self.moving = True
        try:
            fraction_complete = 0.0
            max_displacement = max(abs(v) for v in displacement)
            if block_cancellation:
                time.sleep(0.001 * max_displacement)
            else:
                start_time = time.time()
                while time.time() - start_time < 0.001 * max_displacement:
                    cancel.sleep(0.1)
            fraction_complete = 1.0
        except InvocationCancelledError as e:
            # If the move has been cancelled, stop it but don't handle the exception.
            # We need the exception to propagate in order to stop any calling tasks,
            # and to mark the invocation as "cancelled" rather than stopped.
            fraction_complete = (time.time() - start_time) / (0.001 * max_displacement)
            raise e
        finally:
            self.moving=False
            self.position = {
                k: self.position[k] + int(fraction_complete * v)
                for k, v in zip(self.axis_names, displacement)
            }

    @thing_action
    def move_absolute(self, cancel: CancelHook, block_cancellation: bool=False, **kwargs: Mapping[str, int]):
        """Make an absolute move. Keyword arguments should be axis names."""
        displacement = {
            k: int(v) - self.position[k] 
            for k, v in kwargs.items()
            if k in self.axis_names
        }
        self.move_relative(cancel, block_cancellation=block_cancellation, **displacement)
        
    @thing_action
    def set_zero_position(self):
        """Make the current position zero in all axes
        
        This action does not move the stage, but resets the position to zero.
        It is intended for use after manually or automatically recentring the
        stage.
        """
        self.position = {k: 0 for k in self.axis_names}
