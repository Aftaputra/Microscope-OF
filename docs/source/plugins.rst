Plugins
=======================================================

Introduction
------------
Plugins allow functionality to be added to the OpenFlexure Microscope without having to modify the base code.
They have full access to the :py:class:`openflexure_microscope.Microscope` object, 
including direct access to the attached :py:class:`openflexure_microscope.camera.pi.StreamingCamera` and :py:class:`openflexure_stage.stage.OpenFlexureStage` objects.
This also allows direct access to the :py:class:`picamera.PiCamera` object.

All microscope plugins must subclass :py:class:`openflexure_microscope.plugins.MicroscopePlugin` in order to be loaded by the microscopes :py:class:`openflexure_microscope.plugins.PluginMount`.

Once attached, all methods defined within the plugin class will be accessible from ``<microscope_object>.plugin.<plugin_namespace>.<plugin_method(args)>``.
Here, ``<microscope_object>`` is an instance of :py:class:`openflexure_microscope.Microscope`. The ``<plugin_method>`` is the method defined within your plugin class. Finally, ``<plugin_namespace>`` is determined differently depending on the type of plugin.

Plugins can either be loaded as a single Python file located anywhere on disk, or as a Python package installed to the environment being used. If loaded from a single file, the namespace is set to the file name (excluding .py extension) of the plugin file. If loaded from a package, the namespace is set to the name of the top-level module in the package. For example, if your plugin class definition resides within ``my_openflexure_plugins.microscope.mypluginpackage``, the namespace will be set to ``mypluginpackage``. Where possible, try to use descriptive, unique package names for this reason. For example, rather than name your plugin package ``autofocus``, which would like cause namespace clashes, instead name it ``yourname_autofocus``, or similar.

Module (single-file) plugins
++++++++++++++++++++++++++++
For adding simple functionality, such as a few basic functions and API routes, a single Python file can be loaded as a plugin. 

This Python file must contain all of your plugin classes. Relative imports will not work. External modules and packages can be used with absolute imports, however for more complex plugins, it is often worth instead making use of an installable package plugin.

Package plugins
+++++++++++++++
Generally, for adding anything other than very simple functionality, plugins should be written as `package distributions <https://packaging.python.org/tutorials/packaging-projects/>`_. This has the advantage of allowing relative imports, so functionality can be easily split over several files. For example, class definitions associated with API routes can be separated from class definitions associated with the microscope plugin.

The main restriction is that the plugin package must be importable using an absolute import from within the Python environment being used to load your microscope. 

Loading plugins with microscoperc.yaml
++++++++++++++++++++++++++++++++++++++
Both types of plugin are loaded by specifying the plugin class in your :ref:`MicroscopeRC`. In the case of a single-file plugin, specify the path to the plugin file, followed by the name of your :py:class:`openflexure_microscope.plugins.MicroscopePlugin` child class, separated by a colon. For packaged plugins, specify the absolute module name in place of the path.

For example, the plugins section of your microscoperc.yaml file may look like:

.. code-block:: yaml

    ...
    plugins:
    - openflexure_microscope.plugins.default:Plugin
    - ~/my_plugins/my_plugin_file.py:MyPluginClass
    - my_openflexure_plugins.microscope.mypluginpackage:MyPluginClass
    ...

Microscope plugin structure
---------------------------
As described earlier, a plugin must subclass :py:class:`openflexure_microscope.plugins.MicroscopePlugin`. Each plugin in described by a single class, containing any number of methods. The methods defined within your plugin class will be attached to the microscope. By subclassing :py:class:`openflexure_microscope.plugins.MicroscopePlugin`, your methods automatically get access to the microscope object your plugin is attached to, through ``self.microscope``. This is an instance of :py:class:`openflexure_microscope.Microscope`, and gives unrestricted access to the attached camera and stage hardware.

For example, a simple plugin file named ``myplugin.py``, may look like:

.. code-block:: python

    from openflexure_microscope.plugins import MicroscopePlugin

    class MyPlugin(MicroscopePlugin):

        def identify(self):
            """
            Demonstrate access to Microscope.camera, and Microscope.stage
            """

            parent_camera = self.microscope.camera
            parent_stage = self.microscope.stage

            response = "My parent camera is {}, and my parent stage is {}.".format(parent_camera, 
                                                                                   parent_stage)
            return response

        def hello_world(self):
            """
            Demonstrate passive method
            """

            return "Hello world!"

When this plugin is loaded and attached to a microscope object named ``microscope``, the plugin methods will be available at ``microscope.plugin.myplugin.identify()`` and ``microscope.plugin.myplugin.hello_world()``.

Adding web API routes
---------------------
Plugins can automatically create routes to expose plugin functionality via the web API. Creating API routes for your plugin is strongly recommended, as this is the primary way we encourage interaction with the microscope device.

To create API routes, add a dictionary to your plugin class, named ``api_views``. Within this dictionary, each key should be a string defining the route URL, whose value is a class, subclassing :py:class:`openflexure_microscope.api.v1.views.MicroscopeViewPlugin`.

For example, your ``api_views`` dictionary may look like:

.. code-block:: python

    class MyPluginClass(MicroscopePlugin):

        api_views = {
            '/myplugin': MyRouteAPI,
        }

Here, ``MyRouteAPI`` is a web API plugin class, subclassing :py:class:`openflexure_microscope.api.v1.views.MicroscopeViewPlugin`. If your plugin package were named ``mypluginpackage``, an API route would be automatically added at ``/api/v1/plugin/mypluginpackage/myplugin``.

Parsing JSON from HTTP POST requests
++++++++++++++++++++++++++++++++++++
To ease obtaining values from a JSON payload attached to an HTTP POST request, you can use the :py:class:`openflexure_microscope.api.utilities.JsonPayload` class. This allows parameters to be extracted by their key, with a default value supplied to avoid errors associated with nonexistent keys. Additionally, a converter function may be passed, used in the following examples to convert the type of a value. In principle, however, you can pass any single-argument function and it will apply that function to the value, if it exists.

.. code-block:: python

    ...
    class MyRouteAPI(MicroscopeViewPlugin):

        def post(self):
            # Get payload JSON from request
            payload = JsonPayload(request)

            # Try to find value associated with 'my_string' key.
            # If that key doesn't exist in the payload, return '' instead.
            # If a value does exist, convert it to a string, regardless of its original type.
            new_plugin_string = payload.param('my_string', default='', convert=str)
            ...

.. autoclass:: openflexure_microscope.api.utilities.JsonPayload
    :members:


The MicroscopeViewPlugin class
++++++++++++++++++++++++++++++

All API plugin classes must subclass :py:class:`openflexure_microscope.api.v1.views.MicroscopeViewPlugin`, which is itself a subclass of `Flask's MethodView <http://flask.pocoo.org/docs/1.0/api/#flask.views.MethodView>`_. This greatly simplifies defining different functionality associated with different HTTP methods at a single URL route.
It is best practice to clearly separate out types of functionality by HTTP method. For example, a GET request should never change the state of the microscope. For this, POST or PUT requests are acceptable. Parameters should be passed to POST and PUT requests as JSON payloads, and your methods should include fallback code for cases where parameters are not passed, or are passed in an invalid format. The DELETE method should only be used in situations where your plugin creates additional URL routes for newly created objects, and should serve only to delete these objects and routes.

Each HTTP method maps to a function with the same name, in lowercase. For example, your :py:class:`openflexure_microscope.api.v1.views.MicroscopeViewPlugin` may look like:

.. code-block:: python

    ...
    class MyRouteAPI(MicroscopeViewPlugin):

        def get(self):
            # Call a method from our plugin, using the MicroscopeViewPlugin.plugin shortcut
            data = self.plugin.my_plugin_method()  
            ...

        def post(self):
            # Get payload JSON, and extract a specific value
            payload = JsonPayload(request)
            my_payload_value = payload.param('my_payload_key')
            ...

Accessing the microscope
^^^^^^^^^^^^^^^^^^^^^^^^
All instances of :py:class:`openflexure_microscope.api.v1.views.MicroscopeViewPlugin` must be attached via a microscope plugin. As a result of this, the ``MicroscopeViewPlugin`` class has a ``self.microscope`` attribute, allowing direct access to the :py:class:`openflexure_microscope.Microscope` object. This means that web API plugins can simply chain together basic microscope functions and expose new API routes. No additional microscope functionality is required. However, in most cases web API plugins will serve to provide API routes to new microscope functionality defined in a microscope plugin.

Because of this, instances of MicroscopeViewPlugin have direct access to their associated microscope plugin methods, without needing to know the plugin namespace in advance. As described earlier in this section, all plugins get attached to the microscope in their own namespace, based on the plugins name. This means there are two equivalent ways to access your plugin methods from a web API plugin:

.. code-block:: python

    ...
    # Call a method from our plugin, using the MicroscopeViewPlugin.plugin shortcut
    self.plugin.my_plugin_method()

    # Call a method from our plugin, using the full route
    self.microscope.my_plugin_name.my_plugin_method()
    ...

Example plugin
--------------

.. code-block:: python

    from openflexure_microscope.plugins import MicroscopePlugin
    from openflexure_microscope.api.v1.views import MicroscopeViewPlugin
    from openflexure_microscope.api.utilities import JsonPayload
    
    from flask import request, Response, escape


    ### MICROSCOPE PLUGIN ###

    class MyPluginClass(MicroscopePlugin):
        """
        A set of default plugins
        """

        api_views = {
            '/identify': IdentifyAPI,
            '/hello': HelloWorldAPI,
        }

        def identify(self):
            """
            Demonstrate access to Microscope.camera, and Microscope.stage
            """

            response = "My parent camera is {}, and my parent stage is {}.".format(self.microscope.camera, 
                                                                                   self.microscope.stage)
            return response

        def hello_world(self):
            """
            Demonstrate passive method
            """

            return "Hello world!"


    ### API VIEWS ###

    class IdentifyAPI(MicroscopeViewPlugin):
        """
        A simple example API plugin, attached through the main microscope plugin.
        """
        def get(self):
            """
            Method to call when an HTTP GET request is made.
            """
            # Call a method from our plugin, using the MicroscopeViewPlugin.plugin shortcut
            data = self.plugin.identify()  
            return Response(escape(data))


    class HelloWorldAPI(MicroscopeViewPlugin):
        """
        A method to create, set, and return a new microscope parameter.
        """

        def get(self):
            """
            Method to call when an HTTP GET request is made.
            """

            # If the microscope does not already contain our plugin_string attribute
            if not hasattr(self.microscope, 'plugin_string'):
                # Make a string, using the MicroscopeViewPlugin.plugin shortcut
                self.microscope.plugin_string = self.plugin.hello_world()

            return Response(self.microscope.plugin_string)

        def post(self):
            """
            Method to call when an HTTP POST request is made. 
            Assumes request will include a JSON payload.
            """
            # Get payload JSON
            payload = JsonPayload(request)

            # Extract a value from the JSON key 'plugin_string', and convert to a string. If no value is given, default to empty.
            new_plugin_string = payload.param('plugin_string', default='', convert=str)

            if new_plugin_string:  # If not None or empty
                # Set microscope attribute to the specified string
                self.microscope.plugin_string = new_plugin_string  

            return Response(self.microscope.plugin_string)

In this example, if the package or file were named ``my_plugin``, the two microscope plugin methods would be accessible from ``<microscope_object>.plugin.my_plugin.identify()``, and ``<microscope_object>.plugin.my_plugin.hello_world()``.

Web API routes would automatically be set up at ``/api/v1/plugin/my_plugin/identify`` (GET), and ``/api/v1/plugin/my_plugin/hello`` (GET, POST).

Mounting and built-ins
----------------------
.. toctree::
   :maxdepth: 2

   pluginmounts.rst