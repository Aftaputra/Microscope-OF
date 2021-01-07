import json
import logging

from .error_sources import ErrorSource


def trace_config_exceptions():
    error_sources = []

    from openflexure_microscope.paths import CONFIGURATION_FILE_PATH, SETTINGS_FILE_PATH

    try:
        default_config = json.load(CONFIGURATION_FILE_PATH)
        if not default_config:
            error_sources.append(
                ErrorSource(
                    "Configuration file is missing or empty. This may occur if the server has never been started."
                )
            )
    except Exception as e:  # pylint: disable=W0703
        logging.error("Error parsing config:")
        logging.error(e)
        error_sources.append(
            ErrorSource(
                f"Configuration file is malformed. You can reset to the default configuration by deleting {CONFIGURATION_FILE_PATH}."
            )
        )

    try:
        default_settings = json.load(SETTINGS_FILE_PATH)
        if not default_settings:
            error_sources.append(
                ErrorSource(
                    "Settings file is missing or empty. This may occur if the server has never been started."
                )
            )
    except Exception as e:  # pylint: disable=W0703
        logging.error("Error parsing settings:")
        logging.error(e)
        error_sources.append(
            ErrorSource(
                f"Settings file is malformed. You can reset to the default settings by deleting {SETTINGS_FILE_PATH}."
            )
        )

    return error_sources


def main():
    error_sources = []
    logging.info("Attempting default settings and config import...")
    try:
        from openflexure_microscope import config as _
    except Exception as e:  # pylint: disable=W0703
        error_sources.append(
            ErrorSource(
                "Error importing configuration submodule. This could be an error in our code."
            )
        )
        logging.error("Error importing config:")
        logging.error(e)
        error_sources.extend(trace_config_exceptions())

    return error_sources
