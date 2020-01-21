Adding web API views
====================

Introduction
------------
Extensions can create views to expose extension functionality via the web API. Creating API views for your extension is strongly recommended, as this is the primary way we encourage interaction with the microscope device.

As with most HTTP APIs, we make use of basic HTTP request methods. GET requests return data without modifying any state. POST requests completely replace data with data passed as request arguments. PUT requests update data with new data passed as request arguments. DELETE requests delete a particular object from the server. Your API views need not implement all of these methods.

Continuing our example on the previous page, and discussed below, adding API views may look like:

.. code-block:: python

    from labthings.server.extensions import BaseExtension
    from labthings.server.find import find_component
    from labthings.server.view import View

    from labthings.server.decorators import use_body
    from labthings.server import fields

    ## Extension methods


    def identify(microscope):
        """
        Demonstrate access to Microscope.camera, and Microscope.stage
        """

        response = (
            f"My name is {microscope.name}. "
            f"My parent camera is {microscope.camera}, "
            f"and my parent stage is {microscope.stage}."
        )

        return response


    def rename(microscope, new_name):
        """
        Rename the microscope
        """

        microscope.name = new_name
        microscope.save_settings()


    ## Extension views


    class ExampleIdentifyView(View):
        def get(self):
            # Find our microscope component
            microscope = find_component("org.openflexure.microscope")

            # Return our identify function's output
            return identify(microscope)


    class ExampleRenameView(View):
        # Expect a request parameter called "name", which is a string. Pass to argument "args".
        @use_body(fields.String(required=True, example="My Example Microscope"))
        def post(self, body):
            # Look for our new name in the request body
            new_name = body

            # Find our microscope component
            microscope = find_component("org.openflexure.microscope")

            # Pass microscope and new name to our rename function
            rename(microscope, new_name)

            # Return our identify function's output
            return identify(microscope)


    ## Create extension

    # Create your extension object
    my_extension = BaseExtension("com.myname.myextension", version="0.0.0")

    # Add methods to your extension
    my_extension.add_method(identify, "identify")
    my_extension.add_method(rename, "rename")

    # Add API views to your extension
    my_extension.add_view(ExampleIdentifyView, "/identify")
    my_extension.add_view(ExampleRenameView, "/rename")

Note that we are now passing our microscope object as an argument to our API methods. Finding the microscope component is performed by the API view at request-time, and passed onto the functions.

In this case, our extension will have two new API views at `/identify` and `/rename`. The `/identify` view only accepts GET requests, and the `/rename` view only accepts POST requests.

Request arguments
+++++++++++++++++

For POST and PUT requests, data usually needs to be provided to the view in order to perform its function. In this example, our ``rename`` view requires a new microscope name to be passed. We make use of the ``@use_body`` decorator to provide this functionality.

``@use_body`` defines the type of data expected in the request body. In this example, we ``String`` type data. The arguments of ``fields.String`` allow us to provide additional information, such as the parameter being required, and example values to appear in API documentation.

Adding additional fields, and the meaning of the field types, will be discussed further in the next section.

When a POST request is made to our API view, the request body is converted to processed by `@use_body``, and passed as a positional argument to our ``post`` function. 

Swagger documentation
+++++++++++++++++++++

At this point, it is useful to introduce the automatically generated Swagger documentation. From any web browser, go to ``http://microscope.local/api/v2/swagger-ui`` (or replace ``microscope.local`` with your microscopes IP address on incompatible systems).

This page uses `SwaggerUI <https://swagger.io/tools/swagger-ui/>`_ to provide visual, interactive API documentation. Find your extensions URL in the documentation under the ``extensions`` group. Basic documentation about the parameters required for your POST method should be visible, as well as an interactive example filled out with the example request given in ``@use_body``.