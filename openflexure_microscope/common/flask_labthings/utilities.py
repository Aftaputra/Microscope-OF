from openflexure_microscope.common.labthings_core.utilities import get_docstring
from .schema import Schema, marshmallow, MARSHMALLOW_VERSION_INFO
import collections.abc

from webargs import dict2schema as wa_dict2schema

import logging


def description_from_view(view_class):
    methods = []
    for method_key in ["get", "post", "put", "delete"]:
        if hasattr(view_class, method_key):
            methods.append(method_key.upper())
    brief_description = get_docstring(view_class).partition("\n")[0].strip()

    d = {"methods": methods, "description": brief_description}

    return d


def rupdate(d, u):
    for k, v in u.items():
        if isinstance(v, collections.abc.Mapping):
            if not k in d:
                d[k] = {}
            d[k] = rupdate(d.get(k, {}), v)
        else:
            d[k] = v
    return d