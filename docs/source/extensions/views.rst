Adding web API views
====================

Key terminology
---------------

API View (or View)
++++++++++++++++++

*"A view function is the code you write to respond to requests to your application [...] For RESTful APIs it’s especially helpful to execute a different function for each HTTP method. With the [View class] you can easily do that. Each HTTP method maps to a function with the same name (just in lowercase)"* -  `Flask documentation <https://flask.palletsprojects.com/en/1.1.x/views/>`_

Introduction
------------
Extensions can create views to expose extension functionality via the web API. Creating API views for your extension is strongly recommended, as this is the primary way we encourage interaction with the microscope device.

As with most HTTP APIs, we make use of basic HTTP request methods. GET requests return data without modifying any state. POST requests completely replace data with data passed as request arguments. PUT requests update data with new data passed as request arguments. DELETE requests delete a particular object from the server. Your API views need not implement all of these methods.

Continuing our example on the previous page, and discussed below, adding API views may look like:

.. literalinclude:: ./example_extension/02_adding_views.py

Note that we are now passing our microscope object as an argument to our API methods. Finding the microscope component is performed by the API view at request-time, and passed onto the functions.

Your extension functions can be accessed from within an API View by using ``self.extension``. Once your view has been added to your extension, this will point to the extension object, allowing your API views to use your extension functionality.

In this case, our extension will have two new API views at `/identify` and `/rename`. The `/identify` view only accepts GET requests, and the `/rename` view only accepts POST requests.

Request arguments
+++++++++++++++++

For POST and PUT requests, data usually needs to be provided to the view in order to perform its function. In this example, our ``rename`` view requires a new microscope name to be passed. We make use of the ``args`` class attribute to provide this functionality.

``args`` defines the type of data expected in the request body. In this example, we use ``String`` type data. The arguments of ``fields.String`` allow us to provide additional information, such as the parameter being required, and example values to appear in API documentation.

Adding additional fields, and the meaning of the field types, will be discussed further in the next section.

When a POST request is made to our API view, the server converts the body of the request into a ``String``, and passes it as a positional argument to our ``post`` function.

Swagger documentation
+++++++++++++++++++++

At this point, it is useful to introduce the automatically generated Swagger documentation. From any web browser, go to ``http://microscope.local/api/v2/docs/swagger-ui`` (or replace ``microscope.local`` with your microscope's IP address if ``microscope.local`` doesn't work for your system).

This page uses `SwaggerUI <https://swagger.io/tools/swagger-ui/>`_ to provide visual, interactive API documentation. Find your extensions URL in the documentation under the ``extensions`` group. Basic documentation about the parameters required for your POST method should be visible, as well as an interactive example filled out with the example request given in the view ``schema``.
