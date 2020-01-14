from openflexure_microscope.api.utilities import JsonResponse

from openflexure_microscope.common.labthings_core.utilities import (
    get_by_path,
    set_by_path,
    create_from_path,
)

from openflexure_microscope.common.flask_labthings.find import find_component
from openflexure_microscope.common.flask_labthings.view import View

from openflexure_microscope.common.flask_labthings.decorators import ThingProperty, Tag, doc_response

from flask import jsonify, request, abort
import logging


@ThingProperty
class SettingsProperty(View):
    def get(self):
        """
        Current microscope settings, including camera and stage
        """
        microscope = find_component("org.openflexure.microscope")
        return jsonify(microscope.read_settings())

    def put(self):
        """
        Update current microscope settings, including camera and stage
        """
        microscope = find_component("org.openflexure.microscope")
        payload = JsonResponse(request)

        logging.debug("Updating settings from PUT request:")
        logging.debug(payload.json)

        microscope.apply_settings(payload.json)
        microscope.save_settings()

        return self.get()


@Tag("properties")
class NestedSettingsProperty(View):
    @doc_response(404, description="Settings key cannot be found")
    def get(self, route):
        """
        Show a nested section of the current microscope settings
        """
        microscope = find_component("org.openflexure.microscope")
        keys = route.split("/")

        try:
            value = get_by_path(microscope.read_settings(), keys)
        except KeyError:
            return abort(404)

        return jsonify(value)

    @doc_response(404, description="Settings key cannot be found")
    def put(self, route):
        """
        Update a nested section of the current microscope settings
        """
        microscope = find_component("org.openflexure.microscope")
        keys = route.split("/")
        payload = JsonResponse(request)

        dictionary = create_from_path(keys)
        set_by_path(dictionary, keys, payload.json)

        microscope.apply_settings(dictionary)
        microscope.save_settings()

        return self.get(route)


@ThingProperty
class StatusProperty(View):
    def get(self):
        """
        Show current read-only state of the microscope
        """
        microscope = find_component("org.openflexure.microscope")
        return jsonify(microscope.status)


@Tag("properties")
class NestedStatusProperty(View):
    @doc_response(404, description="Status key cannot be found")
    def get(self, route):
        """
        Show a nested section of the current microscope state
        """
        microscope = find_component("org.openflexure.microscope")
        keys = route.split("/")

        try:
            value = get_by_path(microscope.status, keys)
        except KeyError:
            return abort(404)

        return jsonify(value)
