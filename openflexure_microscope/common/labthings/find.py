from flask import current_app

from . import EXTENSION_NAME


def _current_labthing():
    app = current_app
    if not app:
        return None
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
