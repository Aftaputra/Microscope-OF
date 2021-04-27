import logging
from typing import List, Tuple

from labthings import fields, find_component
from labthings.views import ActionView

from openflexure_microscope.utilities import axes_to_array


class MoveStageAPI(ActionView):
    args = {
        "absolute": fields.Boolean(
            missing=False, example=False, description="Move to an absolute position"
        ),
        "x": fields.Int(missing=None, example=100),
        "y": fields.Int(missing=None, example=100),
        "z": fields.Int(missing=None, example=20),
    }

    def post(self, args):
        """
        Move the microscope stage in x, y, z

        Any axes that are not specifed will not move.
        """
        microscope = find_component("org.openflexure.microscope")

        if not microscope.stage:
            logging.warning("Unable to move. No stage found.")
            return microscope.state["stage"]["position"]

        absolute_move = args.get("absolute")
        move = [0, 0, 0]  # Default to no motion
        for i, axis in enumerate(["x", "y", "z"]):
            if axis in args and args[axis] is not None:
                if absolute_move:
                    # We emulate absolute moves by calculating a relative move that
                    # will take us to the right position.
                    move[i] = args[axis] - microscope.stage.position[i]
                else:
                    move[i] = args[axis]

        logging.debug(f"Moving stage by {move}, request was {args}")

        # Explicitly acquire lock with 1s timeout
        with microscope.stage.lock(timeout=1):
            microscope.stage.move_rel(move)

        return microscope.state["stage"]["position"]


class ZeroStageAPI(ActionView):
    def post(self):
        """
        Zero the stage coordinates.
        Does not move the stage, but rather makes the current position read as [0, 0, 0]
        """
        microscope = find_component("org.openflexure.microscope")

        with microscope.stage.lock(timeout=1):
            microscope.stage.zero_position()

        return microscope.state["stage"]
