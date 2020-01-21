from labthings.server.extensions import BaseExtension
from labthings.server.find import find_component
from labthings.server.view import View

from labthings.server.decorators import (
    use_args,
    marshal_with,
    ThingProperty,
    PropertySchema,
    ThingAction,
    doc_response,
    marshal_task,
)
from labthings.server.schema import Schema
from labthings.server import fields

from flask import send_file  # Used to send images from our server
import io  # Used in our capture action
import time  # Used in our timelapse function

# Used in our timelapse function
from openflexure_microscope.camera.base import generate_basename

# Used to run our timelapse in a background thread
from labthings.core.tasks import taskify

## Extension methods


# Define which properties of a Microscope object we care about,
# and what types they should be converted to
class MicroscopeIdentifySchema(Schema):
    name = fields.String()  # Microscopes name
    id = fields.UUID()  # Microscopes unique ID
    status = fields.Dict()  # Status dictionary
    camera = fields.String()  # Camera object (represented as a string)
    stage = fields.String()  # Stage object (represented as a string)


def rename(microscope, new_name):
    """
    Rename the microscope
    """

    microscope.name = new_name
    microscope.save_settings()


def timelapse(microscope, n_images, t_between):
    """
    Save a set of images in a timelapse

    Args:
        microscope: Microscope object
        n_images (int): Number of images to take
        t_between (int/float): Time, in seconds, between sequential captures
    """
    base_file_name = generate_basename()
    folder = "TIMELAPSE_{}".format(base_file_name)

    # Take exclusive control over both the camera and stage
    with microscope.camera.lock, microscope.stage.lock:
        for n in range(n_images):
            # Generate a filename
            filename = f"{base_file_name}_image{n}"
            # Create a file to save the image to
            output = microscope.camera.new_image(
                filename=filename, folder=folder, temporary=False
            )

            # Capture
            microscope.camera.capture(output.file)

            # Add system metadata
            output.put_metadata(microscope.metadata, system=True)

            # Wait for the specified time
            time.sleep(t_between)


## Extension views

# Since we only have a GET method here, it'll register as a read-only property
@ThingProperty
class ExampleIdentifyView(View):
    # Format our returned object using MicroscopeIdentifySchema
    @marshal_with(MicroscopeIdentifySchema())
    def get(self):
        """
        Show identifying information about the current microscope object
        """
        # Find our microscope component
        microscope = find_component("org.openflexure.microscope")

        # Return our microscope object,
        # let @marshal_with handle formatting the output
        return microscope


@ThingProperty
# We can use a single schema for all methods if the input and output will be formatted identically
# Eg. Here, we will always expect a "name" string argument, and always return a "name" string attribute
@PropertySchema({"name": fields.String(required=True, example="My Example Microscope")})
class ExampleRenameView(View):
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
        # let @marshal_with handle formatting the output
        return microscope


@ThingAction
class QuickCaptureAPI(View):
    """
    Take an image capture and return it without saving
    """

    # Expect a "use_video_port" boolean, which defaults to True if none is given
    @use_args({"use_video_port": fields.Boolean(missing=True)})
    # Our success response (200) returns an image (image/jpeg mimetype)
    @doc_response(200, mimetype="image/jpeg")
    def post(self, args):
        """
        Take a non-persistant image capture.
        """
        # Find our microscope component
        microscope = find_component("org.openflexure.microscope")

        # Open a BytesIO stream to be destroyed once request has returned
        with io.BytesIO() as stream:

            # Capture to our stream object
            microscope.camera.capture(stream, use_video_port=args.get("use_video_port"))

            # Rewind the stream
            stream.seek(0)

            # Return our image data using Flasks send_file function
            return send_file(io.BytesIO(stream.read()), mimetype="image/jpeg")


@ThingAction
class TimelapseAPI(View):
    """
    Take a series of images in a timelapse, running as a background task
    """

    @marshal_task  # Shorthand for marshaling with a pre-made Task object schema
    @use_args(
        {
            "n_images": fields.Integer(
                required=True, example=5, description="Number of images"
            ),
            "t_between": fields.Number(
                missing=1, example=1, description="Time (seconds) between images"
            ),
        }
    )
    def post(self, args):
        # Find our microscope component
        microscope = find_component("org.openflexure.microscope")

        # Create and start "timelapse", running in a background task
        task = taskify(timelapse)(
            microscope, args.get("n_images"), args.get("t_between")
        )

        return task


## Create extension

# Create your extension object
my_extension = BaseExtension("com.myname.myextension", version="0.0.0")

# Add methods to your extension
my_extension.add_method(rename, "rename")

# Add API views to your extension
my_extension.add_view(ExampleIdentifyView, "/identify")
my_extension.add_view(ExampleRenameView, "/rename")
my_extension.add_view(QuickCaptureAPI, "/quick-capture")
my_extension.add_view(TimelapseAPI, "/timelapse")
