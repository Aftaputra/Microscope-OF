from openflexure_microscope.api.utilities import JsonResponse
from openflexure_microscope.common.flask_labthings.resource import Resource
from openflexure_microscope.common.flask_labthings.find import find_device
from openflexure_microscope.utilities import axes_to_array, filter_dict

from flask import Blueprint, jsonify, request

import logging


class MoveStageAPI(Resource):
    def post(self):
        microscope = find_device("openflexure_microscope")
        # Create response object
        payload = JsonResponse(request)
        logging.debug(payload.json)

        # Handle absolute positioning (calculate a relative move from current position and target)
        if (payload.param("absolute") is True) and (
            microscope.stage
        ):  # Only if stage exists
            target_position = axes_to_array(payload.json, ["x", "y", "z"])
            logging.debug("TARGET: {}".format(target_position))
            position = [
                target_position[i] - microscope.stage.position[i] for i in range(3)
            ]
            logging.debug("DELTA: {}".format(position))

        else:
            # Get coordinates from payload
            position = axes_to_array(payload.json, ["x", "y", "z"], [0, 0, 0])

        logging.debug(position)

        # Move if stage exists
        if microscope.stage:
            # Explicitally acquire lock
            with microscope.stage.lock:
                microscope.stage.move_rel(position)
        else:
            logging.warning("Unable to move. No stage found.")

        return jsonify(microscope.status["stage"]["position"])


class ZeroStageAPI(Resource):
    """
    Zero stage coordinates 
    """

    def post(self):
        microscope = find_device("openflexure_microscope")
        microscope.stage.zero_position()

        return jsonify(microscope.status["stage"])
