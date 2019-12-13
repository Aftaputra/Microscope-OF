from flask import current_app, _app_ctx_stack

EXTENSION_NAME = "flask-lab"


class LabThing(object):
    def __init__(self, app=None):
        self.app = app
        self.devices = {}
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.teardown_appcontext(self.teardown)

        app.extensions = getattr(app, "extensions", {})
        app.extensions[EXTENSION_NAME] = self

    def teardown(self, exception):
        print(f"Tearing down devices: {self.devices}")

    def register_device(self, device_object, device_name: str):
        self.devices[device_name] = device_object


def find_device(device_name):
    app = current_app

    if not app:
        return None

    pylot_instance = app.extensions[EXTENSION_NAME]

    if device_name in pylot_instance.devices:
        return pylot_instance.devices[device_name]
    else:
        return None
