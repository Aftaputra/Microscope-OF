from __future__ import annotations
from labthings_fastapi.descriptors.property import PropertyDescriptor
from labthings_fastapi.thing import Thing
from labthings_fastapi.decorators import thing_action, thing_property
from labthings_fastapi.dependencies.invocation import CancelHook
from collections.abc import Sequence, Mapping


class Stage(Thing):
    """A dummy stage for testing purposes
    
    This stage should work similarly to a Sangaboard stage, but without any
    hardware attached.
    """
    _axis_names = ("x", "y", "z")

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
        raise NotImplementedError("Subclasses should implement this method")

    @thing_action
    def move_absolute(self, cancel: CancelHook, block_cancellation: bool=False, **kwargs: Mapping[str, int]):
        """Make an absolute move. Keyword arguments should be axis names."""
        raise NotImplementedError("Subclasses should implement this method")
        
    @thing_action
    def set_zero_position(self):
        """Make the current position zero in all axes
        
        This action does not move the stage, but resets the position to zero.
        It is intended for use after manually or automatically recentring the
        stage.
        """
        raise NotImplementedError("Subclasses should implement this method")
