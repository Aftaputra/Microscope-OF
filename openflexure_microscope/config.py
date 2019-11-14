import json
import os
import errno
import logging
import shutil
import numpy as np
from fractions import Fraction

"""
Attributes:
    USER_CONFIG_DIR (str): Default path of the user-config directory, containing runtime-config and
        calibration files. Obtained from ``os.path.join(os.path.expanduser("~"), ".openflexure")``.
    USER_CONFIG_FILE_PATH (str): Default path of the user microscope_settings.json runtime-config file. 
        Obtained from ``os.path.join(USER_CONFIG_DIR, "microscope_settings.json")``
    user_settings (OpenflexureSettingsFile): Default settings file object, which handles expansion and
        contraction of settings dictionaries.
"""


class JSONEncoder(json.JSONEncoder):
    """
    A custom JSON encoder, with type conversions for PiCamera fractions, Numpy integers, and Numpy arrays
    """
    def default(self, o, markers=None):
        # PiCamera fractions
        if isinstance(o, Fraction):
            return float(o)
        # Numpy integers
        elif isinstance(o, np.integer):
            return int(o)
        # Numpy arrays
        elif isinstance(o, np.ndarray):
            return o.tolist()
        else:
            # call base class implementation which takes care of
            # raising exceptions for unsupported types
            return json.JSONEncoder.default(self, o)


# MAIN CONFIG CLASS

class OpenflexureSettingsFile:
    """
    An object to handle expansion, conversion, and saving of the microscope configuration.

    Args:
        config_path (str): Path to the config JSON file (None falls back to default location)
        expand (bool): Expand paths to valid auxillary config files.
    """

    def __init__(self, config_path: str = None, expand: bool = True):
        global DEFAULT_CONFIG, USER_CONFIG_FILE_PATH

        self.expandable_keys = {
            "camera_settings": None,
            "stage_settings": None,
        }  #: Dictionary of keys that can be passed as a file path string and expanded automatically

        # Set arguments
        self.config_path = config_path or USER_CONFIG_FILE_PATH
        self.expand = expand

        # Initialise basic config file with defaults if it doesn't exist
        initialise_file(self.config_path, populate=DEFAULT_CONFIG)

    def load(self):
        """
        Loads config from a file on-disk, and expands auxillary config files if available.
        """
        # Unexpanded config dictionary (used at load/save time)
        loaded_config = load_json_file(self.config_path)

        # If the loaded config is in contracted format
        if self.expand:
            # Expand self.raw_config into self._config
            loaded_config = self.expand_config(loaded_config)

        logging.debug("Reading settings from disk")
        return loaded_config

    def save(self, config: dict, backup: bool = True):
        """
        Save config to a file on-disk, and splits into auxillary config files if available.
        """
        # If the loaded config was in contracted format
        if self.expand:
            # Contract self._config into self.raw_config
            save_settings = self.contract_config(config)
        else:
            save_settings = config

        if backup:
            if os.path.isfile(self.config_path):
                shutil.copyfile(self.config_path, self.config_path + ".bk")

        logging.debug("Saving settings dictionary to disk")
        save_json_file(self.config_path, save_settings)

    def merge(self, config: dict, backup: bool = True):
        logging.debug("Merging settings with file on disk")
        settings = self.load()
        settings.update(config)

        return settings

    def expand_config(self, config_dict):
        """
        Search a config dictionary for paths to valid auxillary config files,
        and expand into the config dictionary if available.

        Args:
            config_dict (dict): Dictionary of config data to expand
        """
        return_config = {}
        if not config_dict:
            config_dict = {}
        # For each value in the raw loaded config
        for key, value in config_dict.items():
            # If it's a valid expandable parameter
            if key in self.expandable_keys and type(value) is str:

                logging.debug("Expanding {}".format(value))

                # Store expansion path
                self.expandable_keys[key] = config_dict[key]
                # Create the expansion file if it doesn't yet exist
                initialise_file(value)
                # Load the expansion file into _config
                return_config[key] = load_json_file(value) or {}
            else:
                return_config[key] = value

        return return_config

    def contract_config(self, config_dict):
        """
        Split a config dictionary into auxillary config files, if available.

        Args:
            config_dict (dict): Dictionary of config data to contract/split
        """
        return_config = {}
        # For each value in the expanded config
        for key, value in config_dict.items():
            # If it's a valid expandable parameter
            if (
                key in self.expandable_keys
                and self.expandable_keys[key] is not None
                and type(value) is dict
            ):

                logging.debug("Saving to {}".format(self.expandable_keys[key]))
                # Create the file if it doesn't exist
                initialise_file(self.expandable_keys[key])
                # Save the expanded config dictionary to the file
                save_json_file(self.expandable_keys[key], value)
                # Replace the expanded dictionary with a file path
                return_config[key] = self.expandable_keys[key]
            else:
                return_config[key] = value

        return return_config


# HANDLE BASIC LOADING AND SAVING OF SETTINGS FILES

def load_json_file(config_path) -> dict:
    """
    Open a .json config file

    Args:
        config_path (str): Path to the config JSON file. If `None`, defaults to `DEFAULT_CONFIG_PATH`
    """
    config_path = os.path.expanduser(config_path)

    logging.info("Loading {}...".format(config_path))

    with open(config_path) as config_file:
        try:
            config_data = json.load(config_file)
        except json.decoder.JSONDecodeError as e:
            logging.error(e)
            config_data = {}

    # Return loaded config dictionary
    return config_data


def save_json_file(config_path: str, config_dict: dict):
    """
    Save a .json config file

    Args:
        config_dict (dict): Dictionary of config data to save.
        config_path (str): Path to the config JSON file.
    """
    config_path = os.path.expanduser(config_path)

    logging.info("Saving {}...".format(config_path))
    logging.debug(config_dict)

    with open(config_path, "w") as outfile:
        json.dump(config_dict, outfile, cls=JSONEncoder, indent=2, sort_keys=True)


def create_file(config_path):
    if not os.path.exists(os.path.dirname(config_path)):
        try:
            os.makedirs(os.path.dirname(config_path))
        except OSError as exc:  # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise


def initialise_file(config_path, populate: str = "{}\n"):
    """
    Check if a file exists, and if not, create it
    and optionally populate it with content

    Args:
        config_path (str): Path to the file.
        populate (str): String to dump to the file, if it is being newly created
    """
    config_path = os.path.expanduser(config_path)

    logging.debug("Initialising {}".format(config_path))
    logging.debug("Exists: {}".format(os.path.exists(config_path)))

    if not os.path.exists(config_path):  # If user config file doesn't exist
        logging.warning("No config file found at {}. Creating...".format(config_path))
        create_file(config_path)

        logging.info("Populating {}...".format(config_path))
        with open(config_path, "w") as outfile:
            outfile.write(populate)


def settings_file_path(filename: str):
    """Generate a full file path for a filename to be stored in user settings"""
    global USER_CONFIG_DIR
    return os.path.join(USER_CONFIG_DIR, filename)


# HANDLE THE DEFAULT CONFIGURATION FILE

HERE = os.path.abspath(os.path.dirname(__file__))
DEFAULT_CONFIG_FILE_PATH = os.path.join(HERE, "microscope_settings.default.json")

USER_CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".openflexure")
USER_CONFIG_FILE_PATH = os.path.join(USER_CONFIG_DIR, "microscope_settings.json")

# Load the default config
with open(DEFAULT_CONFIG_FILE_PATH, "r") as default_rc:
    DEFAULT_CONFIG = default_rc.read()

# Create the default user settings object
user_settings = OpenflexureSettingsFile(config_path=USER_CONFIG_FILE_PATH, expand=True)
