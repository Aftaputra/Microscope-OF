from flask import Response
from labthings import current_labthing
from labthings.views import View


class APISpecJSONView(View):
    """OpenAPI v3 documentation

    A JSON document containing an API description in OpenAPI format
    """

    def get(self):
        return current_labthing().spec.to_dict()


class APISpecYAMLView(View):
    """OpenAPI v3 documentation
    
    A YAML document containing an API description in OpenAPI format
    """

    def get(self):
        return Response(current_labthing().spec.to_yaml(), mimetype="text/yaml")
