import datetime
import logging
from io import BytesIO

import numpy as np
from flask import send_file
from labthings import find_component
from labthings.views import PropertyView
from PIL import Image


class LSTImageProperty(PropertyView):
    """Gets the lens-shading table as an image"""

    responses = {
        200: {
            "content": {"image/jpeg": {}},
            "description": "Lens-shading table in RGB format",
        }
    }

    def get(self):
        """
        Get the lens shading table as an image.
        """
        microscope = find_component("org.openflexure.microscope")

        # Return intentionally empty response if no LST is available
        if microscope.get_configuration()["camera"]["type"] != "PiCameraStreamer":
            logging.warning("Requested an LST from a non-PiCameraStreamer camera")
            return ("", 204)
        # Return intentionally empty response if we have a valid PiCamera but no LST
        elif getattr(microscope.camera.camera, "lens_shading_table") is None:
            logging.warning("PiCamera.lens_shading_table returned as None")
            return ("", 204)
        else:
            # Get the LST Numpy array from the camera's memoryview
            lst = np.asarray(microscope.camera.camera.lens_shading_table)
            # Create array of R next to G1
            top = np.concatenate(lst[:2], axis=1)
            # Create array of G2 next to B
            bottom = np.concatenate(lst[2:], axis=1)
            # Create combined array of 2x2 grid of greyscale images
            all_channels = np.concatenate((top, bottom), axis=0)
            # Create a PNG
            img_bytes: BytesIO = BytesIO()
            Image.fromarray(np.uint8(all_channels), "L").save(img_bytes, "PNG")
            img_bytes.seek(0)
            # Return the image
            fname: str = f"lst-{datetime.date.today().isoformat()}.png"
            return send_file(img_bytes, as_attachment=True, attachment_filename=fname)
