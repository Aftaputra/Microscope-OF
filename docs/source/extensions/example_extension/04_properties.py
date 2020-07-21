from labthings.extensions import BaseExtension
from labthings import find_component, Schema, fields
from labthings.views import View, PropertyView

## Extension methods


# Define which properties of a Microscope object we care about,
# and what types they should be converted to
class MicroscopeIdentifySchema(Schema):
    name = fields.String()  # Microscopes name
    id = fields.UUID()  # Microscopes unique ID
    state = fields.Dict()  # Status dictionary
    camera = fields.String()  # Camera object (represented as a string)
    stage = fields.String()  # Stage object (represented as a string)


def rename(microscope, new_name):
    """
    Rename the microscope
    """

    microscope.name = new_name
    microscope.save_settings()


## Extension views

# Since we only have a GET method here, it'll register as a read-only property
class ExampleIdentifyView(PropertyView):
    # Format our returned object using MicroscopeIdentifySchema
    schema = MicroscopeIdentifySchema()

    def get(self):
        """
        Show identifying information about the current microscope object
        """
        # Find our microscope component
        microscope = find_component("org.openflexure.microscope")

        # Return our microscope object,
        # let schema handle formatting the output
        return microscope


# We can use a single schema as the input and output will be formatted identically
# Eg. We always expect a "name" string argument, and always return a "name" string attribute
class ExampleRenameView(PropertyView):
    schema = {"name": fields.String(required=True, example="My Example Microscope")}

    def get(self):
        """
        Show the current microscope name
        """
        # Find our microscope component
        microscope = find_component("org.openflexure.microscope")

        return microscope

    def post(self, args):
        """
        Change the current microscope name
        """
        # Look for our "name" parameter in the request arguments
        new_name = args.get("name")

        # Find our microscope component
        microscope = find_component("org.openflexure.microscope")

        # Pass microscope and new name to our rename function
        rename(microscope, new_name)

        # Return our microscope object,
        # let schema handle formatting the output
        return microscope


## Create extension

# Create your extension object
my_extension = BaseExtension("com.myname.myextension", version="0.0.0")

# Add methods to your extension
my_extension.add_method(rename, "rename")

# Add API views to your extension
my_extension.add_view(ExampleIdentifyView, "/identify")
my_extension.add_view(ExampleRenameView, "/rename")
