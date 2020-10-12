from openflexure_microscope.api.utilities import JsonResponse
from labthings.views import View, ActionView
from labthings import find_component, fields

from openflexure_microscope.utilities import axes_to_array, filter_dict

from flask import Blueprint, request

import logging


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
            target_position = axes_to_array(args, ["x", "y", "z"])
            logging.debug("TARGET: {}".format(target_position))
            position = [
                target_position[i] - microscope.stage.position[i] for i in range(3)
            ]
            logging.debug("DELTA: {}".format(position))

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

        # TODO: Make schema for microscope state
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

        # TODO: Make schema for microscope state
        return microscope.state["stage"]

class StageTypeAPI(ActionView):
    args = {
        "stage_type": fields.String(missing = None, example = "SangaStage", description = "The stage geometry [SangaStage, SangaDeltaStage]")
    }
    def post(self,args):
        """
        Set the stage geometry.
        """
        microscope = find_component("org.openflexure.microscope")
        microscope.set_stage(stage_type=args.get("stage_type"))
        return {"stage_type": microscope.configuration["stage"]["type"]}

    def get(self):
        """
        Get the stage geometry.
        """
        microscope = find_component("org.openflexure.microscope")
        return {"stage_type": microscope.configuration["stage"]["type"]}

