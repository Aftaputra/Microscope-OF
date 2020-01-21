from labthings.server.extensions import BaseExtension
from labthings.server.find import find_component


def identify():
    """
    Demonstrate access to Microscope.camera, and Microscope.stage
    """
    microscope = find_component("org.openflexure.microscope")

    parent_camera = microscope.camera
    parent_stage = microscope.stage

    response = "My parent camera is {}, and my parent stage is {}.".format(
        parent_camera, parent_stage
    )
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
my_extension.add_method(rename, "rename")
