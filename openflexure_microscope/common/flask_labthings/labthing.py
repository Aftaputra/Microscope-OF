from flask import url_for, jsonify
from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin

from . import EXTENSION_NAME  # TODO: Move into .names
from .names import TASK_ENDPOINT, TASK_LIST_ENDPOINT, EXTENSION_LIST_ENDPOINT
from .extensions import BaseExtension
from .utilities import description_from_view
from .spec import view2path

from .views.extensions import ExtensionList
from .views.tasks import TaskList, TaskResource
from .views.docs import docs_blueprint, SwaggerUIResource, W3CThingDescriptionResource

from openflexure_microscope.common.labthings_core.utilities import get_docstring

import logging


class LabThing(object):
    def __init__(
        self,
        app=None,
        prefix: str = "",
        title: str = "",
        description: str = "",
        version: str = "0.0.0",
    ):
        self.app = app

        self.devices = {}

        self.extensions = {}

        self.resources = []
        self.properties = {}
        self.actions = {}

        self.endpoints = set()

        self.url_prefix = prefix
        self._description = description
        self._title = title
        self._version = version

        # Store handlers for things like errors and CORS
        self.handlers = {}

        self.spec = APISpec(
            title=self.title,
            version=self.version,
            openapi_version="3.0.2",
            plugins=[MarshmallowPlugin()],
        )

        if app is not None:
            self.init_app(app)

    @property
    def description(self,):
        return self._description

    @description.setter
    def description(self, description: str):
        self._description = description
        self.spec.description = description

    @property
    def title(self,):
        return self._title

    @title.setter
    def title(self, title: str):
        self._title = title
        self.spec.title = title

    @property
    def version(self,):
        return str(self._version)

    @version.setter
    def version(self, version: str):
        self._version = version
        self.spec.version = version

    ### Flask stuff

    def init_app(self, app):
        app.teardown_appcontext(self.teardown)

        # Register Flask extension
        app.extensions = getattr(app, "extensions", {})
        app.extensions[EXTENSION_NAME] = self

        # Add resources, if registered before tying to a Flask app
        if len(self.resources) > 0:
            for resource, urls, endpoint, kwargs in self.resources:
                self._register_view(app, resource, *urls, endpoint=endpoint, **kwargs)

        # Create base routes
        self._create_base_routes()

    def teardown(self, exception):
        pass

    def _create_base_routes(self):
        # Add root representation
        self.app.add_url_rule(self._complete_url("/", ""), "rootrep", self.rootrep)
        # Add thing descriptions
        self.app.register_blueprint(docs_blueprint, url_prefix=self.url_prefix)

        # Add extension overview
        self.add_resource(
            ExtensionList, "/extensions", endpoint=EXTENSION_LIST_ENDPOINT
        )
        self.register_property(ExtensionList)
        # Add task routes
        self.add_resource(TaskList, "/tasks", endpoint=TASK_LIST_ENDPOINT)
        self.register_property(TaskList)
        self.add_resource(TaskResource, "/tasks/<id>", endpoint=TASK_ENDPOINT)

    ### Device stuff

    def register_device(self, device_object, device_name: str):
        self.devices[device_name] = device_object

    ### Extension stuff

    def register_extension(self, extension_object):
        if isinstance(extension_object, BaseExtension):
            self.extensions[extension_object.name] = extension_object
        else:
            raise TypeError("Extension object must be an instance of BaseExtension")

        for extension_view_id, extension_view in extension_object.views.items():
            # Add route to the extensions blueprint
            self.add_resource(
                extension_view["view"],
                "/extensions" + extension_view["rule"],
                **extension_view["kwargs"],
            )

        for prop in extension_object.properties:
            self.register_property(prop)

        for action in extension_object.actions:
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

        logging.debug(f"{endpoint}: {type(resource)}")

        if self.app is not None:
            self._register_view(self.app, resource, *urls, endpoint=endpoint, **kwargs)

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
            # Add the resource to our API spec
            self.spec.path(**view2path(rule, resource, self.spec))

    ### Utilities

    def url_for(self, resource, **values):
        """Generates a URL to the given resource.
        Works like :func:`flask.url_for`."""
        endpoint = resource.endpoint
        return url_for(endpoint, **values)

    def owns_endpoint(self, endpoint):
        return endpoint in self.endpoints

    ### Description
    def rootrep(self):
        """
        Root representation
        """
        # TODO: Allow custom root representations

        rr = {
            "id": url_for("rootrep", _external=True),
            "title": self.title,
            "description": self.description,
            "links": {
                "thingDescription": {
                    "href": url_for("labthings_docs.w3c_td", _external=True),
                    "description": get_docstring(W3CThingDescriptionResource),
                },
                "swaggerUI": {
                    "href": url_for("labthings_docs.swagger_ui", _external=True),
                    **description_from_view(SwaggerUIResource),
                },
                "extensions": {
                    "href": self.url_for(ExtensionList, _external=True),
                    **description_from_view(ExtensionList),
                },
                "tasks": {
                    "href": self.url_for(TaskList, _external=True),
                    **description_from_view(TaskList),
                },
            },
        }

        return jsonify(rr)
