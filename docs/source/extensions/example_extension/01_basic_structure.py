from labthings import find_component
from labthings.extensions import BaseExtension


# Create the extension class
class MyExtension(BaseExtension):
    def __init__(self):
        # Superclass init function
        super().__init__("com.myname.myextension", version="0.0.0")

    def identify(self):
        """
        Demonstrate access to Microscope.camera, and Microscope.stage
        """
        microscope = find_component("org.openflexure.microscope")

        response = (
            f"My name is {microscope.name}. "
            f"My parent camera is {microscope.camera}, "
            f"and my parent stage is {microscope.stage}."
        )

        return response

    def rename(self, new_name):
        """
        Rename the microscope
        """

        microscope = find_component("org.openflexure.microscope")

        microscope.name = new_name
        microscope.save_settings()


LABTHINGS_EXTENSIONS = (MyExtension,)
