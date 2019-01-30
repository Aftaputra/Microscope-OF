from flask import jsonify
from werkzeug.exceptions import default_exceptions
from werkzeug.exceptions import HTTPException

from pprint import pprint

class JSONExceptionHandler(object):

    def __init__(self, app=None):
        if app:
            self.init_app(app)

    def std_handler(self, error):
        message = error.description if isinstance(error, HTTPException) else error.message
        status_code = error.code if isinstance(error, HTTPException) else 500

        response = {
            'status_code': status_code,
            'message': message
        }
        return jsonify(response)


    def init_app(self, app):
        self.app = app
        self.register(HTTPException)
        for code, v in default_exceptions.items():
            self.register(code)

    def register(self, exception_or_code, handler=None):
        self.app.errorhandler(exception_or_code)(handler or self.std_handler)