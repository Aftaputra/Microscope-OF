import logging
from flask import current_app

from . import EXTENSION_NAME


def _current_labthing():
    app = current_app._get_current_object()
    if not app:
        return None
    logging.debug("Active app extensions:")
    logging.debug(app.extensions)
    logging.debug("Active labthing:")
    logging.debug(app.extensions[EXTENSION_NAME])
    return app.extensions[EXTENSION_NAME]


def registered_plugins(labthing_instance=None):
    if not labthing_instance:
        labthing_instance = _current_labthing()
    return labthing_instance.plugins


def registered_devices(labthing_instance=None):
    if not labthing_instance:
        labthing_instance = _current_labthing()
    return labthing_instance.devices


def find_device(device_name, labthing_instance=None):
    if not labthing_instance:
        labthing_instance = _current_labthing()

    if device_name in labthing_instance.devices:
        return labthing_instance.devices[device_name]
    else:
        return None

def find_plugin(plugin_name, labthing_instance=None):
    if not labthing_instance:
        labthing_instance = _current_labthing()

    logging.debug("Current labthing:")
    logging.debug(_current_labthing())

    if plugin_name in labthing_instance.plugins:
        return labthing_instance.plugins[plugin_name]
    else:
        return None
