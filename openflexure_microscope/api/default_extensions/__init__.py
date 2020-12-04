import logging
import traceback
from contextlib import contextmanager
from typing import List, Type

from labthings.extensions import BaseExtension

LABTHINGS_EXTENSIONS: List[Type[BaseExtension]] = []


@contextmanager
def handle_extension_error(extension_name):
    """'gracefully' log an error if an extension fails to load."""
    try:
        yield
    except Exception:  # pylint: disable=W0703
        logging.error(
            "Exception loading builtin extension %s: \n%s",
            extension_name,
            traceback.format_exc(),
        )


with handle_extension_error("autofocus"):
    from .autofocus import AutofocusExtension

    LABTHINGS_EXTENSIONS.append(AutofocusExtension)
with handle_extension_error("scan"):
    from .scan import ScanExtension

    LABTHINGS_EXTENSIONS.append(ScanExtension)
with handle_extension_error("zip builder"):
    from .zip_builder import ZipBuilderExtension

    LABTHINGS_EXTENSIONS.append(ZipBuilderExtension)
with handle_extension_error("autostorage"):
    from .autostorage import AutostorageExtension

    LABTHINGS_EXTENSIONS.append(AutostorageExtension)

with handle_extension_error("lens shading calibration"):
    from .picamera_autocalibrate import LSTExtension

    LABTHINGS_EXTENSIONS.append(LSTExtension)

with handle_extension_error("camera stage mapping"):
    from .camera_stage_mapping import CSMExtension

    LABTHINGS_EXTENSIONS.append(CSMExtension)
