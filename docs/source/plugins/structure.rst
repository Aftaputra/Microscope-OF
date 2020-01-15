Basic extension structure
=========================

An extension starts as a simple instance of :py:class:`openflexure_microscope.common.flask_labthings.extensions.BaseExtension`. 
Each extension is described by a single ``BaseExtension`` instance, containing any number of methods, API views, and additional hardware components. 

In order to access the currently running microscope object, use the :py:func:`openflexure_microscope.common.flask_labthings.find` function, with the argument ``"org.openflexure.microscope"``. Likewise, any new components attached by other extensions can be found using their full name, as above.

A simple extension file, with no API views but application-available methods may look like:

.. code-block:: python

    from openflexure_microscope.common.flask_labthings.extensions import BaseExtension
    from openflexure_microscope.common.flask_labthings.find import find_component


    def identify():
        """
        Demonstrate access to Microscope.camera, and Microscope.stage
        """
        microscope = find_component("org.openflexure.microscope")

        parent_camera = microscope.camera
        parent_stage = microscope.stage

        response = "My parent camera is {}, and my parent stage is {}.".format(parent_camera, 
                                                                                parent_stage)
        return response

    def rename(new_name):
        """
        Rename the microscope
        """

        microscope = find_component("org.openflexure.microscope")

        microscope.name = new_name
        microscope.save_settings()
    

    # Create your extension object
    my_extension = BaseExtension("com.myname.myextension", version="0.0.0")

    # Add methods to your extension
    my_extension.add_method(identify, "identify")
    my_extension.add_method(hello_world, "rename")


Once this extension is loaded, any other extensions will have access to your methods:

.. code-block:: python

    from openflexure_microscope.common.flask_labthings.find import find_extension

    def test_extension_method():
        # Find your extension. Returns None if it hasn't been found.
        my_found_extension = find_extension("com.myname.myextension")

        # Call a function from your extension
        if my_found_extension:
            my_found_extension.identify()