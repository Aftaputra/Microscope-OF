import logging

from .error_sources import ErrorSource

picamera_import_error = ErrorSource(
    (
        "Picamera module could not be imported.",
        "Check physical connections to the camera as it may be damaged or disconnected.",
    )
)

picamera_errors = (
    "Camera is not enabled. Try running 'sudo raspi-config' and ensure that the camera has been enabled.",
)


def main():
    error_sources = []
    logging.info("Attempting to import picamera...")

    try:
        from picamerax import PiCamera
    except Exception as e:  # pylint: disable=W0703
        # TODO: Parse exception object for a few different issues, and append
        # different error sources E.g. pi with camera already in use,
        # disconnected, unsupported OS, etc
        logging.error(e)
        error_sources.append(picamera_import_error)
    else:
        import picamerax.exc.PiCameraError

        try:
            cam = PiCamera()
        except picamerax.exc.PiCameraError as e:
            if e.args[0] in picamera_errors:
                error_sources.append(ErrorSource(e.args[0]))

    return error_sources
