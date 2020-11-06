import logging
import os
import sys

from .error_sources import bcolors

from openflexure_microscope.paths import (
    FALLBACK_OPENFLEXURE_VAR_PATH,
    PREFERRED_OPENFLEXURE_VAR_PATH,
)

from . import check_capture_reload, check_settings, check_picamera, check_sangaboard

# Paths for suggestions
LOGS_PATHS = [
    os.path.join(PREFERRED_OPENFLEXURE_VAR_PATH, "logs"),
    os.path.join(FALLBACK_OPENFLEXURE_VAR_PATH, "logs"),
]
SETTINGS_PATHS = [
    os.path.join(var_path, "settings", "microscope_settings.json")
    for var_path in (PREFERRED_OPENFLEXURE_VAR_PATH, FALLBACK_OPENFLEXURE_VAR_PATH)
]
CONFIG_PATHS = [
    os.path.join(var_path, "settings", "microscope_configuration.json")
    for var_path in (PREFERRED_OPENFLEXURE_VAR_PATH, FALLBACK_OPENFLEXURE_VAR_PATH)
]
DATA_PATHS = [
    os.path.join(PREFERRED_OPENFLEXURE_VAR_PATH, "data"),
    os.path.join(FALLBACK_OPENFLEXURE_VAR_PATH, "data"),
]

# Look for debug flag
logger = logging.getLogger()
if "-d" in sys.argv or "--debug" in sys.argv:
    logger.setLevel(logging.DEBUG)
    logging.debug("Testing debug logger. One two one two.")
else:
    logger.setLevel(logging.INFO)


if __name__ == "__main__":
    spoof = False

    error_sources = []

    error_sources.extend(check_settings.main())
    error_sources.extend(check_picamera.main())
    error_sources.extend(check_capture_reload.main())
    error_sources.extend(check_sangaboard.main())

    if not error_sources:
        print()
        print(bcolors.OKGREEN + "No errors found!" + bcolors.ENDC)
        print(
            "That's not to say everything is fine, only that our automatic diagnostics couldn't find much."
        )
        print(f"You can check through the server logs at {LOGS_PATHS}")

    else:
        print()
        for err in error_sources:
            print(err.message)
