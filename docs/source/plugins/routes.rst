Adding web API routes
=====================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

Introduction
------------
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
------------------------------------
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
------------------------------

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