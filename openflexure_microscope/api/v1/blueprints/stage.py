from openflexure_microscope.api.utilities import parse_payload, get_from_payload, gen, get_bool
from openflexure_microscope.api.v1.views import MicroscopeView

from flask import Response, Blueprint, jsonify, request

import logging


class PositionAPI(MicroscopeView):

    def get(self):
        """
        Return current x, y and z positions of the stage.

        .. :quickref: Position; Get current position

        **Example request**:

        .. sourcecode:: http

          GET /stage/position/ HTTP/1.1
          Accept: application/json

        **Example response**:

        .. sourcecode:: http

          HTTP/1.1 200 OK
          Vary: Accept
          Content-Type: application/json

          {
            "x": 0, 
            "y": 0, 
            "z": 0
          }

        :>json int x: x steps
        :>json int y: y steps
        :>json int z: z steps
        """
        return jsonify(self.microscope.state['stage']['position'])

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
        # Get payload
        state = parse_payload(request)
        logging.debug(state)

        # Construct position array
        position = [0, 0, 0]

        # Handle absolute positioning
        if 'absolute' in state and state['absolute'] is True:
            # Get coordinates from payload
            for axis, key in enumerate(['x', 'y', 'z']):
                if key in state:
                    position[axis] = int(state[key]-self.microscope.stage.position[axis])

        else:
            # Get coordinates from payload
            for axis, key in enumerate(['x', 'y', 'z']):
                if key in state:
                    position[axis] = int(state[key])

        logging.debug(position)

        self.microscope.stage.move_rel(position)

        return jsonify(self.microscope.state['stage']['position'])


class StageParamsAPI(MicroscopeView):

    def get(self):
        """
        Return current parameters of the stage.

        .. :quickref: Stage params; Get current stage parameters

        **Example request**:

        .. sourcecode:: http

          GET /stage/params HTTP/1.1
          Accept: application/json

        **Example response**:

        .. sourcecode:: http

          HTTP/1.1 200 OK
          Vary: Accept
          Content-Type: application/json

          {
            "backlash": {
                "x": 0, 
                "y": 0, 
                "z": 128
            }, 
          }

        """

        return jsonify(self.microscope.state['stage'])

    def post(self):
        """
        Set parameters of the stage.

        .. :quickref: Stage params; Set current stage parameters

        :reqheader Accept: application/json
        :<json json backlash:   - **x** *(int)*: x-axis backlash in steps
                                - **y** *(int)*: y-axis backlash in steps
                                - **z** *(int)*: x-axis backlash in steps

        """
        # Get payload
        state = parse_payload(request)
        logging.debug(state)

        # BACKLASH
        if 'backlash' in state:
            # Construct backlash array
            backlash = [0, 0, 0]

            # Get backlash coordinates from payload
            for axis, key in enumerate(['x', 'y', 'z']):
                if key in state['backlash']:
                    backlash[axis] = int(state['backlash'][key])

            # Apply backlash
            self.microscope.stage.backlash = backlash

        return jsonify(self.microscope.state['stage'])


def construct_blueprint(microscope_obj):

    blueprint = Blueprint('stage_blueprint', __name__)

    blueprint.add_url_rule(
        '/position',
        view_func=PositionAPI.as_view('position', microscope=microscope_obj)
    )

    blueprint.add_url_rule(
        '/params',
        view_func=StageParamsAPI.as_view('stage_params', microscope=microscope_obj)
    )

    return(blueprint)
