from openflexure_microscope.api.utilities import JsonResponse
from openflexure_microscope.api.views import MicroscopeView
from openflexure_microscope.utilities import axes_to_array, filter_dict

from flask import Blueprint, jsonify, request

import logging


class MoveStageAPI(MicroscopeView):
    """
    Handle stage movements. 
    """

    def post(self):
        """
        Set x, y and z positions of the stage.

        .. :quickref: Position; Update current position

        :reqheader Accept: application/json
        :<json boolean absolute: (true) move to absolute position, (false) move by relative amount
        :<json boolean force: allow moving by more than programmed limit
        :<json int x: x steps
        :<json int y: y steps
        :<json int z: z steps

        """
        # Create response object
        payload = JsonResponse(request)
        logging.debug(payload.json)

        # Handle absolute positioning (calculate a relative move from current position and target)
        if (payload.param("absolute") is True) and (
            self.microscope.stage
        ):  # Only if stage exists
            target_position = axes_to_array(payload.json, ["x", "y", "z"])
            logging.debug("TARGET: {}".format(target_position))
            position = [
                target_position[i] - self.microscope.stage.position[i] for i in range(3)
            ]
            logging.debug("DELTA: {}".format(position))

        else:
            # Get coordinates from payload
            position = axes_to_array(payload.json, ["x", "y", "z"], [0, 0, 0])

        logging.debug(position)

        # Move if stage exists
        if self.microscope.stage:
            # Explicitally acquire lock
            with self.microscope.stage.lock:
                self.microscope.stage.move_rel(position)

        return jsonify(self.microscope.status["stage"]["position"])
