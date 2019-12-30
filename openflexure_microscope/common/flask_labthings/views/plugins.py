"""
Top-level representation of attached and enabled plugins
"""

from openflexure_microscope.common.labthings_core.utilities import get_docstring
from ..utilities import description_from_view

from openflexure_microscope.common.flask_labthings.resource import Resource
from openflexure_microscope.common.flask_labthings.find import registered_plugins
from openflexure_microscope.common.flask_labthings.schema import Schema
from openflexure_microscope.common.flask_labthings.decorators import marshal_with
from openflexure_microscope.common.flask_labthings import fields
from marshmallow import pre_dump

from flask import jsonify, url_for

import logging


class PluginSchema(Schema):
    name = fields.String(data_key="title")
    _name_python_safe = fields.String(data_key="pythonName")
    _cls = fields.String(data_key="pythonObject")
    gui = fields.Dict()
    description = fields.String()

    links = fields.Dict()

    # TODO: Automate this somewhat
    @pre_dump
    def generate_links(self, data, **kwargs):
        d = {}
        for view_id, view_data in data.views.items():
            view_cls = view_data["view"]
            view_kwargs = view_data["kwargs"]
            # Make links dictionary if it doesn't yet exist
            d[view_id] = {
                "href": url_for(view_cls.endpoint, **view_kwargs, _external=True),
                **description_from_view(view_cls),
            }

        data.links = d

        return data


class PluginListResource(Resource):
    @marshal_with(PluginSchema(many=True))
    def get(self):
        """
        Return the current plugin forms

        .. :quickref: Plugin; Get forms

        Returns an array of present plugin forms (describing plugin user interfaces.)
        Please note, this is *not* a list of all enabled plugins, only those with associated
        user interface forms.

        A complete list of enabled plugins can be found in the microscope state.

        """
        return registered_plugins().values()
