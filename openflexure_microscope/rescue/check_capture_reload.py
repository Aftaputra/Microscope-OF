import logging

from openflexure_microscope.captures.capture import (
    EXIF_FORMATS,
    build_captures_from_exif,
    make_file_list,
)
from openflexure_microscope.captures.capture_manager import BASE_CAPTURE_PATH
from openflexure_microscope.config import user_settings
from openflexure_microscope.rescue.monitor_timeout import launch_timeout_test_process

from .error_sources import ErrorSource, WarningSource


def check_capture_reload(cap_path):
    logging.info("Starting capture reload with a 60 second timeout...")
    passed_timeout_test = launch_timeout_test_process(
        build_captures_from_exif, args=(cap_path,), timeout=60
    )

    return passed_timeout_test


def main():
    error_sources = []

    logging.info("Loading user settings...")
    settings = user_settings.load()
    cap_path = str(settings.get("captures", {}).get("paths", {}).get("default"))
    logging.info("Capture path found: %s", cap_path)

    if not cap_path:
        logging.error(
            "No capture path defined in settings. This is unusual for anything other than a first-run. \nFalling back to default path."
        )
        cap_path = BASE_CAPTURE_PATH

    # Check number of captures being restored
    files = make_file_list(cap_path, EXIF_FORMATS)
    if len(files) >= 10000:
        error_sources.append(
            WarningSource(
                (
                    "Over 10000 captures are being restored. This may slow down server startup.",
                    f"Consider moving your captures from {cap_path} to another location.",
                )
            )
        )

    # Check restore time of captures
    passed_timeout = check_capture_reload(cap_path)
    if not passed_timeout:
        error_sources.append(
            ErrorSource(
                (
                    "Capture database rebuilding took a long time. This may not cause catastrophic errors, but rather will cause the server to hang for a while.",
                    f"To fix, consider moving your captures from {cap_path} to another location.",
                )
            )
        )

    return error_sources
