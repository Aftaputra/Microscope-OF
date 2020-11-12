import logging

from flask import abort
from labthings import find_component, fields
from labthings.marshalling import use_args
from labthings.utilities import create_from_path, get_by_path, set_by_path
from labthings.views import PropertyView, View


class SettingsProperty(PropertyView):
    def get(self):
        """
        Current microscope settings, including camera and stage
        """
        microscope = find_component("org.openflexure.microscope")
        return microscope.read_settings()

    @use_args(fields.Dict())
    def put(self, args):
        """
        Update current microscope settings, including camera and stage
        """
        microscope = find_component("org.openflexure.microscope")

        logging.debug("Updating settings from PUT request:")
        logging.debug(args)

        microscope.update_settings(args)
        microscope.save_settings()

        return self.get()


class NestedSettingsProperty(View):
    tags = ["properties"]
    responses = {404: {"description": "Settings key cannot be found"}}

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

        return value

    @use_args(fields.Dict())
    def put(self, args, route):
        """
        Update a nested section of the current microscope settings
        """
        microscope = find_component("org.openflexure.microscope")
        keys = route.split("/")

        dictionary = create_from_path(keys)
        set_by_path(dictionary, keys, args)

        microscope.update_settings(dictionary)
        microscope.save_settings()

        return self.get(route)


class StateProperty(PropertyView):
    def get(self):
        """
        Show current read-only state of the microscope
        """
        microscope = find_component("org.openflexure.microscope")
        return microscope.state


class NestedStateProperty(View):
    tags = ["properties"]
    responses = {404: {"description": "Status key cannot be found"}}

    def get(self, route):
        """
        Show a nested section of the current microscope state
        """
        microscope = find_component("org.openflexure.microscope")
        keys = route.split("/")

        try:
            value = get_by_path(microscope.state, keys)
        except KeyError:
            return abort(404)

        return value


class ConfigurationProperty(PropertyView):
    def get(self):
        """
        Show current read-only state of the microscope
        """
        microscope = find_component("org.openflexure.microscope")
        return microscope.configuration


class NestedConfigurationProperty(View):
    tags = ["properties"]
    responses = {404: {"description": "Status key cannot be found"}}

    def get(self, route):
        """
        Show a nested section of the current microscope state
        """
        microscope = find_component("org.openflexure.microscope")
        keys = route.split("/")

        try:
            value = get_by_path(microscope.configuration, keys)
        except KeyError:
            return abort(404)

        return value
