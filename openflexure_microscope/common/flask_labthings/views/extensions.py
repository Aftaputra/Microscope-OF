"""
Top-level representation of attached and enabled Extensions
"""

from openflexure_microscope.common.labthings_core.utilities import get_docstring
from ..utilities import description_from_view

from openflexure_microscope.common.flask_labthings.resource import Resource
from openflexure_microscope.common.flask_labthings.find import registered_extensions
from openflexure_microscope.common.flask_labthings.schema import Schema
from openflexure_microscope.common.flask_labthings.decorators import marshal_with
from openflexure_microscope.common.flask_labthings import fields
from marshmallow import pre_dump

from flask import jsonify, url_for

import logging


class ExtensionSchema(Schema):
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
            view_rule = view_data["rule"]
            # Make links dictionary if it doesn't yet exist
            d[view_id] = {
                "href": url_for(ExtensionListResource.endpoint, **view_kwargs, _external=True) + view_rule,
                **description_from_view(view_cls),
            }

        data.links = d

        return data


class ExtensionListResource(Resource):
    """
    List and basic documentation for all enabled Extensions
    """

    @marshal_with(ExtensionSchema(many=True))
    def get(self):
        """
        Return the current Extension forms

        .. :quickref: Extension; Get forms

        Returns an array of present Extension forms (describing Extension user interfaces.)
        Please note, this is *not* a list of all enabled Extensions, only those with associated
        user interface forms.

        A complete list of enabled Extensions can be found in the microscope state.

        """
        return registered_extensions().values()
