import logging
import os
import platform
import sys

import pkg_resources

from openflexure_microscope.paths import (
    FALLBACK_OPENFLEXURE_VAR_PATH,
    PREFERRED_OPENFLEXURE_VAR_PATH,
)

from . import (
    check_capture_reload,
    check_picamera,
    check_sangaboard,
    check_settings,
    check_system,
)
from .error_sources import bcolors

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
    logger.setLevel(logging.WARNING)


def main():
    print()
    print(bcolors.HEADER + "OpenFlexure Rescue" + bcolors.ENDC)
    print()
    print(
        "This script attempts to identify common issues for a microscope not working properly."
    )
    print(
        "It is not designed to identify bugs in the code, but rather configuration or setup issues."
    )
    print()
    print("Any identified warnings [?] or errors [!] will be reported.")
    print()

    error_sources = []

    error_sources.extend(check_system.main())
    error_sources.extend(check_settings.main())
    error_sources.extend(check_picamera.main())
    error_sources.extend(check_capture_reload.main())
    error_sources.extend(check_sangaboard.main())

    dist = pkg_resources.get_distribution("openflexure-microscope-server")

    print()
    print(f"Server Version: {dist.version}")
    print(f"Platform: {platform.platform()}")

    if not error_sources:
        print()
        print(bcolors.OKGREEN + "No issues found!" + bcolors.ENDC)
        print(
            "That's not to say everything is fine, only that our automatic diagnostics couldn't find much."
        )
        print(f"You can check through the server logs at {LOGS_PATHS}")

    else:
        print()
        for err in error_sources:
            print(err.message)


if __name__ == "__main__":
    main()
