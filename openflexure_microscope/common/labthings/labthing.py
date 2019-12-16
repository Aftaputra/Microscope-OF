from flask import current_app, _app_ctx_stack, request

from .plugins import BasePlugin
from .views.plugins import PluginListResource

from . import EXTENSION_NAME


class LabThing(object):
    def __init__(self, app=None, prefix="", description=""):
        self.app = app

        self.devices = {}

        self.plugins = {}

        self.resources = []
        self.endpoints = set()

        self.url_prefix = prefix
        self.description = description

        if app is not None:
            self.init_app(app)

    ### Flask stuff

    def init_app(self, app):
        app.teardown_appcontext(self.teardown)

        app.extensions = getattr(app, "extensions", {})
        app.extensions[EXTENSION_NAME] = self

        self._create_base_routes()

    def teardown(self, exception):
        print(f"Tearing down devices: {self.devices}")

    def _create_base_routes(self):
        self.add_resource(PluginListResource, "/plugins")

    ### Device stuff

    def register_device(self, device_object, device_name: str):
        self.devices[device_name] = device_object

    ### Plugin stuff
    def register_plugin(self, plugin_object):
        if isinstance(plugin_object, BasePlugin):
            self.plugins[plugin_object.name] = plugin_object
        else:
            raise TypeError("Plugin object must be an instance of BasePlugin")

        # TODO: Add plugin routes

    ### Resource stuff

    def _complete_url(self, url_part, registration_prefix):
        """This method is used to defer the construction of the final url in
        the case that the Api is created with a Blueprint.
        :param url_part: The part of the url the endpoint is registered with
        :param registration_prefix: The part of the url contributed by the
            blueprint.  Generally speaking, BlueprintSetupState.url_prefix
        """
        parts = [registration_prefix, self.url_prefix, url_part]
        return "".join([part for part in parts if part])

    def add_resource(self, resource, *urls, **kwargs):
        """Adds a resource to the api.
        :param resource: the class name of your resource
        :type resource: :class:`Type[Resource]`
        :param urls: one or more url routes to match for the resource, standard
                    flask routing rules apply.  Any url variables will be
                    passed to the resource method as args.
        :type urls: str
        :param endpoint: endpoint name (defaults to :meth:`Resource.__name__.lower`
            Can be used to reference this route in :class:`fields.Url` fields
        :type endpoint: str
        :param resource_class_args: args to be forwarded to the constructor of
            the resource.
        :type resource_class_args: tuple
        :param resource_class_kwargs: kwargs to be forwarded to the constructor
            of the resource.
        :type resource_class_kwargs: dict
        Additional keyword arguments not specified above will be passed as-is
        to :meth:`flask.Flask.add_url_rule`.
        Examples::
            api.add_resource(HelloWorld, '/', '/hello')
            api.add_resource(Foo, '/foo', endpoint="foo")
            api.add_resource(FooSpecial, '/special/foo', endpoint="foo")
        """
        if self.app is not None:
            self._register_view(self.app, resource, *urls, **kwargs)
        else:
            self.resources.append((resource, urls, kwargs))

    def resource(self, *urls, **kwargs):
        """Wraps a :class:`~flask_restful.Resource` class, adding it to the
        api. Parameters are the same as :meth:`~flask_restful.Api.add_resource`.
        Example::
            app = Flask(__name__)
            api = restful.Api(app)
            @api.resource('/foo')
            class Foo(Resource):
                def get(self):
                    return 'Hello, World!'
        """

        def decorator(cls):
            self.add_resource(cls, *urls, **kwargs)
            return cls

        return decorator

    def _register_view(self, app, resource, *urls, **kwargs):
        endpoint = kwargs.pop("endpoint", None) or resource.__name__.lower()
        self.endpoints.add(endpoint)
        resource_class_args = kwargs.pop("resource_class_args", ())
        resource_class_kwargs = kwargs.pop("resource_class_kwargs", {})

        # NOTE: 'view_functions' is cleaned up from Blueprint class in Flask 1.0
        if endpoint in getattr(app, "view_functions", {}):
            previous_view_class = app.view_functions[endpoint].__dict__["view_class"]

            # if you override the endpoint with a different class, avoid the collision by raising an exception
            if previous_view_class != resource:
                raise ValueError(
                    "This endpoint (%s) is already set to the class %s."
                    % (endpoint, previous_view_class.__name__)
                )

        resource.endpoint = endpoint
        resource_func = resource.as_view(
            endpoint, *resource_class_args, **resource_class_kwargs
        )

        for url in urls:
            # If we've got no Blueprint, just build a url with no prefix
            rule = self._complete_url(url, "")
            # Add the url to the application or blueprint
            app.add_url_rule(rule, view_func=resource_func, **kwargs)
