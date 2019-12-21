from flask import url_for, jsonify

from .plugins import BasePlugin
from .views.plugins import PluginListResource
from .views.tasks import TaskList, TaskResource

from openflexure_microscope.common.labthings_core.utilities import get_docstring
from .exceptions import JSONExceptionHandler

from . import EXTENSION_NAME


class LabThing(object):
    def __init__(self, app=None, prefix: str = "", title: str = "", description: str = "", handle_errors: bool = True):
        self.app = app

        self.devices = {}

        self.plugins = {}

        self.resources = []
        self.properties = {}
        self.actions = {}

        self.endpoints = set()

        self.url_prefix = prefix
        self.description = description
        self.title = title

        if handle_errors:
            self.error_handler = JSONExceptionHandler()
        else:
            self.error_handler = None

        if app is not None:
            self.init_app(app)

    ### Flask stuff

    def init_app(self, app):
        app.teardown_appcontext(self.teardown)

        # Register Flask extension
        app.extensions = getattr(app, "extensions", {})
        app.extensions[EXTENSION_NAME] = self

        # Register error handler if one exists
        if self.error_handler:
            self.error_handler.init_app(self.app)

        # Create base routes
        self._create_base_routes()

        # Add resources, if registered before tying to a Flask app
        if len(self.resources) > 0:
            for resource, urls, endpoint, kwargs in self.resources:
                self._register_view(app, resource, *urls, endpoint=endpoint, **kwargs)

    def teardown(self, exception):
        pass

    def _create_base_routes(self):
        # Add thing description to root
        self.app.add_url_rule(self._complete_url("/td", ""), "td", self.td)
        # Add plugin overview
        self.add_resource(PluginListResource, "/plugins")
        self.register_property(PluginListResource)
        # Add task routes
        self.add_resource(TaskList, "/tasks")
        self.register_property(TaskList)
        self.add_resource(TaskResource, "/tasks/<id>")

    ### Device stuff

    def register_device(self, device_object, device_name: str):
        self.devices[device_name] = device_object

    ### Plugin stuff

    def register_plugin(self, plugin_object):
        if isinstance(plugin_object, BasePlugin):
            self.plugins[plugin_object.name] = plugin_object
        else:
            raise TypeError("Plugin object must be an instance of BasePlugin")

        for plugin_view_id, plugin_view in plugin_object.views.items():
            # Add route to the plugins blueprint
            self.add_resource(
                plugin_view["view"],
                "/plugins" + plugin_view["rule"],
                **plugin_view["kwargs"],
            )

        for prop in plugin_object.properties:
            self.register_property(prop)

        for action in plugin_object.actions:
            self.register_action(action)

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

    def register_property(self, resource):
        if hasattr(resource, "endpoint"):
            self.properties[resource.endpoint] = resource
        else:
            raise RuntimeError(
                f"Resource {resource} has not yet been added. Cannot set as a property."
            )

    def register_action(self, resource):
        if hasattr(resource, "endpoint"):
            self.actions[resource.endpoint] = resource
        else:
            raise RuntimeError(
                f"Resource {resource} has not yet been added. Cannot set as an action."
            )

    def add_resource(self, resource, *urls, endpoint=None, **kwargs):
        """Adds a resource to the api.
        :param resource: the class name of your resource
        :type resource: :class:`Type[Resource]`
        :param urls: one or more url routes to match for the resource, standard
                    flask routing rules apply.  Any url variables will be
                    passed to the resource method as args.
        :type urls: str
        :param endpoint: endpoint name (defaults to :meth:`Resource.__name__`
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
        endpoint = endpoint or resource.__name__.lower()
        if self.app is not None:
            self._register_view(self.app, resource, *urls, endpoint=endpoint, **kwargs)
        else:
            self.resources.append((resource, urls, endpoint, kwargs))

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

    def _register_view(self, app, resource, *urls, endpoint=None, **kwargs):
        endpoint = endpoint or resource.__name__.lower()
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

    ### Utilities

    def url_for(self, resource, **values):
        """Generates a URL to the given resource.
        Works like :func:`flask.url_for`."""
        endpoint = resource.endpoint
        return url_for(endpoint, **values)

    def owns_endpoint(self, endpoint):
        """Tests if an endpoint name (not path) belongs to this Api.  Takes
        in to account the Blueprint name part of the endpoint name.
        :param endpoint: The name of the endpoint being checked
        :return: bool
        """

        if self.blueprint:
            if endpoint.startswith(self.blueprint.name):
                endpoint = endpoint.split(self.blueprint.name + '.', 1)[-1]
            else:
                return False
        return endpoint in self.endpoints

    ### Description

    def td(self):
        """
        W3C-style Thing Description
        """
        props = {}
        for key, prop in self.properties.items():
            props[key] = {}
            props[key]["title"] = prop.__name__
            props[key]["description"] = get_docstring(prop)
            props[key]["links"] = [{"href": self.url_for(prop, _external=True)}]

        actions = {}
        for key, prop in self.actions.items():
            actions[key] = {}
            actions[key]["title"] = prop.__name__
            actions[key]["description"] = get_docstring(prop)
            actions[key]["links"] = [{"href": self.url_for(prop, _external=True)}]

        td = {
            "id": url_for("td", _external=True),
            "title": self.title,
            "description": self.description,
            "properties": props,
            "actions": actions,
        }

        return jsonify(td)

    # TODO: Add a nicer root resource like the old self-documenting system