from openflexure_microscope.devel import (
    MicroscopeViewPlugin,
    JsonResponse,
    request,
    jsonify,
    taskify,
)

import logging


class DoAPI(MicroscopeViewPlugin):
    """
    A dynamic example API plugin
    """

    def get(self):
        values = {"val_int": self.plugin.val_int}
        return jsonify(values)

    def post(self):
        self.plugin.val_int += 1

        return jsonify({"response": "completed"})
