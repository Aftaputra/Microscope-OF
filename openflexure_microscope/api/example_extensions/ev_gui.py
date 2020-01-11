from openflexure_microscope.common.flask_labthings.resource import Resource
from openflexure_microscope.common.flask_labthings.extensions import BaseExtension
from openflexure_microscope.common.flask_labthings.decorators import (
    ThingAction,
    ThingProperty,
)

from openflexure_microscope.api.utilities.gui import expand_routes

import logging

from flask import jsonify

# Some value that will change over time
# Here, we add 1 to it every time a GET request is made
val_int = 0


def dynamic_form():
    return {
        "id": "test-plugin",
        "icon": "pets",
        "forms": [
            {
                "name": "Simple request",
                "isCollapsible": False,
                "isTask": False,
                "selfUpdate": True,
                "route": "/do",
                "submitLabel": "Do things",
                "schema": [
                    {
                        "fieldType": "numberInput",
                        "name": "val_int",
                        "label": "Number value",
                        "minValue": 0,
                    },
                    {
                        "fieldType": "htmlBlock",
                        "name": "html_block",
                        "content": f"<i>Value is: </i><br>{val_int}.",  # We dynamically use the val_int variable
                    },
                ],
            }
        ],
    }


# Alternate form without any dynamic parts
static_form = {
    "id": "test-plugin",
    "icon": "pets",
    "forms": [
        {
            "name": "Simple request",
            "isCollapsible": False,
            "isTask": False,
            "selfUpdate": True,
            "route": "/do",
            "submitLabel": "Do things",
            "schema": [
                {
                    "fieldType": "numberInput",
                    "name": "val_int",
                    "label": "Number value",
                    "minValue": 0,
                },
                {
                    "fieldType": "htmlBlock",
                    "name": "html_block",
                    "content": f"<i>Value is fixed</i>.",
                },
            ],
        }
    ],
}


@ThingProperty
class TestAPIView(Resource):
    def get(self):
        global val_int
        val_int += 1
        return jsonify({"val": True})


@ThingAction
class TestDoAPIView(Resource):
    def post(self):
        global val_int
        val_int += 1
        return jsonify({"val": True})


# Using the dynamic form
dynamic_test_extension_v2 = BaseExtension("dynamic_test_extension")
dynamic_test_extension_v2.add_view(
    TestAPIView, "/get", endpoint="dynamic_test_extension_get"
)
dynamic_test_extension_v2.add_view(
    TestDoAPIView, "/do", endpoint="dynamic_test_extension_do"
)

dynamic_test_extension_v2.add_meta(
    "gui", expand_routes(dynamic_form, dynamic_test_extension_v2)
)


# Using the static form
static_test_extension_v2 = BaseExtension("static_test_extension")
static_test_extension_v2.add_view(
    TestAPIView, "/get", endpoint="static_test_extension_get"
)
static_test_extension_v2.add_view(
    TestDoAPIView, "/do", endpoint="static_test_extension_do"
)
static_test_extension_v2.add_meta(
    "gui", expand_routes(static_form, static_test_extension_v2)
)
