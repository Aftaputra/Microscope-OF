Basic plugin structure
===========================

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