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
        "x": fields.Int(missing=0, example=100),
        "y": fields.Int(missing=0, example=100),
        "z": fields.Int(missing=0, example=20),
    }

    def post(self, args):
        """
        Move the microscope stage in x, y, z
        """
        microscope = find_component("org.openflexure.microscope")

        # Handle absolute positioning (calculate a relative move from current position and target)
        if (args.get("absolute")) and (microscope.stage):  # Only if stage exists
            target_position: List[int] = axes_to_array(args, ["x", "y", "z"])
            logging.debug("TARGET: %s", (target_position))
            position: Tuple[int, int, int] = (
                target_position[i] - microscope.stage.position[i] for i in range(3)
            )
            logging.debug("DELTA: %s", (position))

        else:
            # Get coordinates from payload
            position = axes_to_array(args, ["x", "y", "z"], [0, 0, 0])

        logging.debug(position)

        # Move if stage exists
        if microscope.stage:
            # Explicitally acquire lock with 1s timeout
            with microscope.stage.lock(timeout=1):
                microscope.stage.move_rel(position)
        else:
            logging.warning("Unable to move. No stage found.")

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
