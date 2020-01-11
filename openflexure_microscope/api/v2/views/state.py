from openflexure_microscope.api.utilities import JsonResponse

from openflexure_microscope.common.labthings_core.utilities import (
    get_by_path,
    set_by_path,
    create_from_path,
)

from openflexure_microscope.common.flask_labthings.find import find_device
from openflexure_microscope.common.flask_labthings.resource import Resource

from openflexure_microscope.common.flask_labthings.decorators import ThingProperty

from flask import jsonify, request, abort
import logging


@ThingProperty
class SettingsProperty(Resource):
    def get(self):
        microscope = find_device("org.openflexure.microscope")
        return jsonify(microscope.read_settings())

    def put(self):
        microscope = find_device("org.openflexure.microscope")
        payload = JsonResponse(request)

        logging.debug("Updating settings from PUT request:")
        logging.debug(payload.json)

        microscope.apply_settings(payload.json)
        microscope.save_settings()

        return self.get()


class NestedSettingsProperty(Resource):
    def get(self, route):
        microscope = find_device("org.openflexure.microscope")
        keys = route.split("/")

        try:
            value = get_by_path(microscope.read_settings(), keys)
        except KeyError:
            return abort(404)

        return jsonify(value)

    def put(self, route):
        microscope = find_device("org.openflexure.microscope")
        keys = route.split("/")
        payload = JsonResponse(request)

        dictionary = create_from_path(keys)
        set_by_path(dictionary, keys, payload.json)

        microscope.apply_settings(dictionary)
        microscope.save_settings()

        return self.get(route)


@ThingProperty
class StatusProperty(Resource):
    def get(self):
        microscope = find_device("org.openflexure.microscope")
        return jsonify(microscope.status)


class NestedStatusProperty(Resource):
    def get(self, route):
        microscope = find_device("org.openflexure.microscope")
        keys = route.split("/")

        try:
            value = get_by_path(microscope.status, keys)
        except KeyError:
            return abort(404)

        return jsonify(value)
