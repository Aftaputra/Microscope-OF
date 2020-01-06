from .resource import BaseResource
from .utilities import rupdate
from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin

from openflexure_microscope.common.labthings_core.utilities import (
    get_docstring,
    get_summary,
)

from .fields import Field
from marshmallow import Schema as BaseSchema

from collections import Mapping


def update_spec(obj, spec):
    obj.__apispec__ = obj.__dict__.get("__apispec__", {})
    rupdate(obj.__apispec__, spec)
    return obj.__apispec__


def view2path(rule: str, view: BaseResource, spec: APISpec):
    params = {
        "path": rule,  # TODO: Validate this slightly (leading / etc)
        "operations": view2operations(view, spec),
        "description": get_docstring(view),
        "summary": get_summary(view),
    }

    if hasattr(view, "__apispec__"):
        # Recursively update params
        rupdate(params, view.__apispec__)

    return params


def view2operations(view: BaseResource, spec: APISpec, populate_default: bool = True):
    ops = {}
    for method in BaseResource.methods:
        if hasattr(view, method):
            # Populate with default responses
            if populate_default:
                ops[method] = {
                    "responses": {
                        200: {
                            "description": get_summary(getattr(view, method))
                            or "Success"
                        },
                        404: {"description": "Resource not found"},
                    }
                }
            else:
                ops[method] = {}

            rupdate(
                ops[method],
                {
                    "description": get_docstring(getattr(view, method)),
                    "summary": get_summary(getattr(view, method)),
                },
            )

            if hasattr(getattr(view, method), "__apispec__"):
                rupdate(
                    ops[method], doc2operation(getattr(view, method).__apispec__, spec)
                )

    return ops


def doc2operation(apispec: dict, spec: APISpec):
    op = {}
    if "_params" in apispec:
        rupdate(
            op,
            {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": convert_schema(apispec.get("_params"), spec)
                        }
                    }
                }
            },
        )

    if "_schema" in apispec:
        rupdate(
            op,
            {
                "responses": {
                    200: {
                        "content": {
                            "application/json": {
                                "schema": convert_schema(apispec.get("_schema"), spec)
                            }
                        }
                    }
                }
            },
        )

    for key, val in apispec.items():
        if not key in ["_params", "_schema"]:
            op[key] = val

    return op


def convert_schema(schema, spec: APISpec):
    if isinstance(schema, BaseSchema):
        return schema
    elif isinstance(schema, Mapping):
        return map2properties(schema, spec)
    else:
        raise TypeError(
            "Unsupported schema type. Ensure schema is a Schema class, or dictionary of Field objects"
        )


def map2properties(schema, spec: APISpec):
    marshmallow_plugin = next(
        plugin for plugin in spec.plugins if isinstance(plugin, MarshmallowPlugin)
    )
    converter = marshmallow_plugin.converter

    d = {}
    for k, v in schema.items():
        if isinstance(v, Field):
            d[k] = converter.field2property(v)
        elif isinstance(v, Mapping):
            d[k] = map2properties(v, spec)
        else:
            d[k] = v

    return {"properties": d}
