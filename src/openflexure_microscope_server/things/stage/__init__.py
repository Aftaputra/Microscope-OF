"""A package for stage control Things.

`BaseStage` is the base class that provides core stage functionality, but
no hardware interface control. To create a stage Thing to control a specific
piece of hardware the BaseStage should be subclassed, and any method raising
a NotImplementedError should be created.

As the object will be used as a context manager create the hardware connection in
``__enter__`` (not in ``__init__``), and close the connection with ``__exit__``.
"""

from __future__ import annotations
from collections.abc import Sequence, Mapping
from typing import Literal

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


class BaseStage(lt.Thing):
    """A base stage class for OpenFlexure translation stages.

    This can't be used directly but should reduce boilerplate code when
    implementing new stages.

    Note that the coordinate system used for the microscope may need to have different
    axis direction as those used for

    A minimal working stage must implement ``_hardware_move_relative``
    and ``_hardware_move_absolute`` actions, which update the ``_hardware_position``
    attribute on completion, and also should implement ``set_zero_position``.
    """

    _axis_names = ("x", "y", "z")

    def __init__(self):
        """Initialise the stage.

        :raises RedefinedBaseMovementError: if ``move_relative`` and/or
        ``move_absolute`` are overridden. It is recommended to override
        ``_hardware_move_relative`` and/or ``_hardware_move_absolute`` instead so that
        all code in the child class uses the hardware reference frame.
        """
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

    @lt.thing_property
    def axis_names(self) -> Sequence[str]:
        """The names of the stage's axes, in order."""
        return self._axis_names

    @lt.thing_property
    def position(self) -> Mapping[str, int]:
        """Current position of the stage."""
        return self._apply_axis_direction(self._hardware_position)

    moving = lt.ThingProperty(
        bool,
        False,
        readonly=True,
        observable=True,
    )
    """Whether the stage is in motion."""

    axis_inverted = lt.ThingSetting(
        initial_value={"x": False, "y": False, "z": False},
        model=Mapping[str, bool],
        readonly=True,
    )
    """Used to convert coordinates between the program frame and the hardware frame."""

    def _apply_axis_direction(
        self, position: list[int] | tuple[int] | Mapping[str | int]
    ) -> list[int] | Mapping[str | int]:
        if isinstance(position, (list, tuple)):
            return [
                -pos if inverted else pos
                for pos, inverted in zip(position, self.axis_inverted.values())
            ]
        if isinstance(position, Mapping):
            try:
                return {
                    ax: -position[ax] if self.axis_inverted[ax] else position[ax]
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
    def thing_state(self):
        """Summary metadata describing the current state of the stage."""
        return {"position": self.position}

    @lt.thing_action
    def invert_axis_direction(self, axis: Literal["x", "y", "z"]):
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

    @lt.thing_action
    def move_relative(
        self,
        cancel: lt.deps.CancelHook,
        block_cancellation: bool = False,
        **kwargs: Mapping[str, int],
    ):
        """Make a relative move. Keyword arguments should be axis names."""
        self._hardware_move_relative(
            cancel=cancel,
            block_cancellation=block_cancellation,
            **self._apply_axis_direction(kwargs),
        )

    def _hardware_move_relative(
        self,
        cancel: lt.deps.CancelHook,
        block_cancellation: bool = False,
        **kwargs: Mapping[str, int],
    ):
        """Make a relative move in the coordinate system used by the physical hardware.

        Make sure to use and update `self._hardware_position` not `self.position`.
        """
        raise NotImplementedError(
            "StageThings must define their own _hardware_move_relative method"
        )

    @lt.thing_action
    def move_absolute(
        self,
        cancel: lt.deps.CancelHook,
        block_cancellation: bool = False,
        **kwargs: Mapping[str, int],
    ):
        """Make an absolute move. Keyword arguments should be axis names."""
        self._hardware_move_absolute(
            cancel=cancel,
            block_cancellation=block_cancellation,
            **self._apply_axis_direction(kwargs),
        )

    def _hardware_move_absolute(
        self,
        cancel: lt.deps.CancelHook,
        block_cancellation: bool = False,
        **kwargs: Mapping[str, int],
    ):
        """Make a absolute move in the coordinate system used by the physical hardware.

        Make sure to use and update `self._hardware_position` not `self.position`.
        """
        raise NotImplementedError(
            "StageThings must define their own move_absolute method"
        )

    @lt.thing_action
    def set_zero_position(self):
        """Make the current position zero in all axes.

        This action does not move the stage, but resets the position to zero.
        It is intended for use after manually or automatically recentring the
        stage.
        """
        raise NotImplementedError(
            "StageThings must define their own set_zero_position method"
        )

    @lt.thing_action
    def get_xyz_position(self) -> tuple[int, int, int]:
        """Return a tuple containing (x, y, z) position.

        :raises KeyError: if this stage does not have axes named "x", "y", and "z".

        This method provides the interface expected by the camera_stage_mapping.
        """
        position_dict = self.position
        return (position_dict["x"], position_dict["y"], position_dict["z"])

    @lt.thing_action
    def move_to_xyz_position(
        self, cancel: lt.deps.CancelHook, xyz_pos: tuple[int, int, int]
    ) -> None:
        """Move to the location specified by an (x, y, z) tuple.

        :param cancel: A cancel hook for cancelling the move. This dependency should be
            injected automatically by LabThings-FastAPI
        :param xyz_pos: The (x, y, z) position to move to.

        :raises KeyError: if this stage does not have axes named "x", "y", and "z".

        This method provides the interface expected by the camera_stage_mapping.
        """
        self.move_absolute(cancel=cancel, x=xyz_pos[0], y=xyz_pos[1], z=xyz_pos[2])


StageDependency = lt.deps.direct_thing_client_dependency(BaseStage, "/stage/")
