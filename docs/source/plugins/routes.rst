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

The MicroscopeViewPlugin class
------------------------------

All API plugin classes must subclass :py:class:`openflexure_microscope.api.v1.views.MicroscopeViewPlugin`, which is itself a subclass of `Flask's MethodView <http://flask.pocoo.org/docs/1.0/api/#flask.views.MethodView>`_. This greatly simplifies defining different functionality associated with different HTTP methods at a single URL route.
It is best practice to clearly separate out types of functionality by HTTP method. For example, a GET request should never change the state of the microscope. For this, POST or PUT requests are acceptable. Parameters should be passed to POST and PUT requests as JSON payloads, and your methods should include fallback code for cases where parameters are not passed, or are passed in an invalid format. The DELETE method should only be used in situations where your plugin creates additional URL routes for newly created objects, and should serve only to delete these objects and routes.

Each HTTP method maps to a function with the same name, in lowercase. For example, your :py:class:`openflexure_microscope.api.v1.views.MicroscopeViewPlugin` may look like:

.. code-block:: python

    from flask import jsonify
    ...
    class MyRouteAPI(MicroscopeViewPlugin):

        def get(self):
            # Retrieve some information, without changing the state of the microscope
            ...

        def post(self):
            # Change the state of the microscope based on passed parameters
            ...

Sometimes you will need to create variable API routes. For example, the built-in routes for managing capture data use capture IDs in the request URL to specify which capture data should be returned. Plugins can also access this functionality. This is done using `Flask variable rules <http://flask.pocoo.org/docs/1.0/quickstart/#variable-rules>`_. Here, variables are added to the URL route string by marking them with ``<variable_name>``, which then passes ``variable_name`` to your request function as a keyword argument.

For example:

.. code-block:: python

    class MyPluginClass(MicroscopePlugin):

        api_views = {
            '/myplugin/<object_id>': MyRouteAPI,
        }
    ...

    class MyRouteAPI(MicroscopeViewPlugin):

        def get(self, object_id):
            # Retrieve some information about object_id
            this_object = object_dictionary[object_id]
            ...

Calling plugin methods from routes
++++++++++++++++++++++++++++++++++

Instances of MicroscopeViewPlugin have direct access to their associated microscope plugin methods, without needing to know the plugin namespace in advance. As described earlier in this section, all plugins get attached to the microscope in their own namespace, based on the plugins name. This means there are two equivalent ways to access your plugin methods from a web API plugin:

.. code-block:: python

    ...
    # Call a method from our plugin, using the MicroscopeViewPlugin.plugin shortcut
    self.plugin.my_plugin_method()

    # Call a method from our plugin, using the full route
    self.microscope.my_plugin_name.my_plugin_method()
    ...

Building responses
++++++++++++++++++

Since we are using Flask as our web framework, you're able to return any type of `Flask response <http://flask.pocoo.org/docs/1.0/quickstart/#about-responses>`_ to be passed back to the client. However, since the server is designed to be accessed by clients as a simple API, it is **strongly** recommended that responses are JSON formatted. Both GET and POST methods should return a JSON object describing the current state of the microscope relevant to the action performed. 

Fortunately, Flask includes a ``jsonify`` method to convert any Python dictionary into a valid JSON response. See the `Flask documentation <http://flask.pocoo.org/docs/1.0/api/#flask.json.jsonify>`_ for more information. 

It is also possible to create HTTP errors using the `Flask abort method <http://flask.pocoo.org/docs/1.0/api/#flask.abort>`_. This is useful particularly if your route handles multiple resources such as captures. In the case that a client tries to modify or get the state of a nonexistent resource, you can return (for example) ``abort(404)``, or some other `more relevant HTTP error code <https://en.wikipedia.org/wiki/List_of_HTTP_status_codes>`_. 

An example web route with simple responses may look like:

.. code-block:: python

    from flask import jsonify
    ...

    class MyPluginClass(MicroscopePlugin):

        api_views = {
            '/myplugin/<object_id>': MyRouteAPI,
        }
    ...

    class MyRouteAPI(MicroscopeViewPlugin):

        def get(self, object_id):

            # If the requested object doesn't exist
            if not object_id in object_dictionary:
                # Abort with error 404. This prevents raising a nonspecific exception later
                abort(404)

            # Retrieve some information, now we're sure the reqested object exists
            this_object = object_dictionary[object_id]

            # Make a dictionary of the data to return
            data = {
                'id': this_object.id,
                'name': this_object.name
                'object_value', this_object.value
            }

            # Return the JSON representation of our data dictionary
            return jsonify(data)
            ...

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
