import os
import logging

# UTILITIES


def check_rw(path):
    return os.access(path, os.W_OK) and os.access(path, os.R_OK)


def settings_file_path(filename: str):
    """Generate a full file path for a filename to be stored in server settings folder"""
    return os.path.join(OPENFLEXURE_ETC_PATH, filename)


def data_file_path(filename: str):
    """Generate a full file path for a filename to be stored in server data folder"""
    return os.path.join(OPENFLEXURE_VAR_PATH, filename)


# HANDLE DEFAULTS FILES STORED IN THIS APPLICATION

HERE = os.path.abspath(os.path.dirname(__file__))

#: Path of default (first-run) microscope settings
DEFAULT_CONFIG_FILE_PATH = os.path.join(HERE, "microscope_settings.default.json")


# DATA BASE PATHS

if os.name == "nt":
    PREFERRED_VAR_PATH = os.getenv("PROGRAMDATA") or "C:\\ProgramData"
    FALLBACK_VAR_PATH = os.path.expanduser("~")
else:
    PREFERRED_VAR_PATH = "/var"
    FALLBACK_VAR_PATH = os.path.expanduser("~")

PREFERRED_OPENFLEXURE_VAR_PATH = os.path.join(PREFERRED_VAR_PATH, "openflexure")
FALLBACK_OPENFLEXURE_VAR_PATH = os.path.join(FALLBACK_VAR_PATH, "openflexure")

if not os.path.exists(PREFERRED_OPENFLEXURE_VAR_PATH) and check_rw(PREFERRED_VAR_PATH):
    os.makedirs(PREFERRED_OPENFLEXURE_VAR_PATH)

if check_rw(PREFERRED_OPENFLEXURE_VAR_PATH):
    OPENFLEXURE_VAR_PATH = PREFERRED_OPENFLEXURE_VAR_PATH
else:
    if not os.path.exists(FALLBACK_OPENFLEXURE_VAR_PATH):
        os.makedirs(FALLBACK_OPENFLEXURE_VAR_PATH)
    OPENFLEXURE_VAR_PATH = FALLBACK_OPENFLEXURE_VAR_PATH


# SERVER BASE PATHS

if os.name == "nt":
    PREFERRED_ETC_PATH = os.getenv("PROGRAMDATA") or "C:\\ProgramData"
    FALLBACK_ETC_PATH = os.path.expanduser("~")
else:
    PREFERRED_ETC_PATH = "/etc"
    FALLBACK_ETC_PATH = os.path.join(os.path.expanduser("~"), ".config")

PREFERRED_OPENFLEXURE_ETC_PATH = os.path.join(PREFERRED_ETC_PATH, "openflexure")
FALLBACK_OPENFLEXURE_ETC_PATH = os.path.join(FALLBACK_ETC_PATH, "openflexure")

if not os.path.exists(PREFERRED_OPENFLEXURE_ETC_PATH) and check_rw(PREFERRED_ETC_PATH):
    os.makedirs(PREFERRED_OPENFLEXURE_ETC_PATH)

if check_rw(PREFERRED_OPENFLEXURE_ETC_PATH):
    OPENFLEXURE_ETC_PATH = PREFERRED_OPENFLEXURE_ETC_PATH
else:
    if not os.path.exists(FALLBACK_OPENFLEXURE_ETC_PATH):
        os.makedirs(FALLBACK_OPENFLEXURE_ETC_PATH)
    OPENFLEXURE_ETC_PATH = FALLBACK_OPENFLEXURE_ETC_PATH


# SERVER PATHS

#: Path of microscope settings directory
CONFIG_FILE_PATH = os.path.join(OPENFLEXURE_ETC_PATH, "microscope_settings.json")
#: Path of microscope extensions directory
OPENFLEXURE_EXTENSIONS_PATH = os.path.join(
    OPENFLEXURE_ETC_PATH, "microscope_extensions"
)


# DATA PATHS
