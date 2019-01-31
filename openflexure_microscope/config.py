import yaml
import os
import errno
import logging
import shutil
import copy
from fractions import Fraction
from collections import abc

HERE = os.path.abspath(os.path.dirname(__file__))
DEFAULT_CONFIG_PATH = os.path.join(HERE, 'microscoperc.default.yaml')

USER_CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".openflexure")  #: str: Default path of the user-config directory, containing runtime-config and calibration files. Obtained from ``os.path.join(os.path.expanduser("~"), ".openflexure")``.
USER_CONFIG_FILE = os.path.join(USER_CONFIG_DIR, "microscoperc.yaml")  #: str: Default path of the user microscoperc.yaml runtime-config file. Obtained from ``os.path.join(USER_CONFIG_DIR, "microscoperc.yaml")``

with open(DEFAULT_CONFIG_PATH, 'r') as default_rc:
    DEFAULT_CONFIG = default_rc.read()

JSON_TYPE_TABLE = {

}


def json_convert(v):
    """Make an individual attribute JSON-safe"""
    if isinstance(v, Fraction):
        return float(v)
    else:
        return v


def to_map(data, func):
    """
    Recursively apply a function to a dictionary, list, array, or tuple

    Args:
        data: Input iterable data
        func: Function to apply to all non-iterable values
        excluded_keys: Any dictionary keys to exclude from the returned data
    """
    # If the object is a dictionary
    if isinstance(data, abc.Mapping):
        return {key: to_map(val, func) for key, val in data.items()}
    # If the object is iterable but NOT a dictionary or a string
    elif (isinstance(data, abc.Iterable) and
          not isinstance(data, abc.Mapping) and
          not isinstance(data, str)):
        return [to_map(x, func) for x in data]
    # if the object is neither a map nor iterable
    else:
        return func(data)


def json_map(data, clean_keys=True):
    """
    Make a copy of an input dictionary that's safe for JSON return

    Args:
        data: Input dictionary
        clean_keys: Modify any keys unsuitable for JSON return

    """

    # Do not overwrite original data dictionary
    d = copy.copy(data)

    # If we're cleaning up unsuitable keys
    if clean_keys:
        # Convert lens_shading_table to a bool
        if 'picamera_settings' in d and 'lens_shading_table' in d['picamera_settings']:
            logging.debug("Bool-ifying lens_shading_table")
            if d['picamera_settings']['lens_shading_table'] is not None:
                d['picamera_settings']['lens_shading_table'] = True

    return to_map(d, json_convert)


def load_yaml_file(config_path) -> dict:
    """
    Open a .yaml config file

    Args:
        config_path (str): Path to the config YAML file. If `None`, defaults to `DEFAULT_CONFIG_PATH`
    """
    config_path = os.path.expanduser(config_path)

    logging.info("Loading {}...".format(config_path))

    with open(config_path) as config_file:
        config_data = yaml.load(config_file)

    # Return loaded config dictionary
    return config_data


def save_yaml_file(config_path: str, config_dict: dict, safe: bool = False):
    """
    Save a .yaml config file

    Args:
        config_dict (dict): Dictionary of config data to save.
        config_path (str): Path to the config YAML file.
        safe (bool): Whether to use PyYAML safe_dump instead of dump
    """
    config_path = os.path.expanduser(config_path)

    logging.info("Saving {}...".format(config_path))

    with open(config_path, 'w') as outfile:
        if not safe:
            yaml.dump(config_dict, outfile)
        else:
            yaml.safe_dump(config_dict, outfile)


def create_file(config_path):
    if not os.path.exists(os.path.dirname(config_path)):
        try:
            os.makedirs(os.path.dirname(config_path))
        except OSError as exc:  # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise


def initialise_file(config_path, populate: str = ""):
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
        with open(config_path, 'w') as outfile:
            outfile.write(populate)


class OpenflexureConfig:

    def __init__(self, config_path: str = None, expand: bool = True):
        global DEFAULT_CONFIG, USER_CONFIG_FILE

        self.expandable_keys = {
            'picamera_settings': None,
            'openflexure_stage_settings': None
        }  #: Dictionary of keys that can be passed as a file path string and expanded automatically

        # Set arguments
        self.config_path = config_path or USER_CONFIG_FILE
        self.expand = expand

        # Create empty config dictionaries
        self._config = {}

        # Initialise basic config file with defaults if it doesn't exist
        initialise_file(self.config_path, populate=DEFAULT_CONFIG)

        # Load the config in, setting self._config and self.config
        self.load()

    @property
    def config(self):
        return self.read()

    def read(self, json_safe=False):
        if json_safe:
            logging.info("Reading config as JSON-safe dictionary")
            return json_map(self._config)
        else:
            logging.info("Reading config directly")
            return self._config

    def write(self, update_dict: dict):
        self._config.update(update_dict)

    def load(self):
        # Unexpanded config dictionary (used at load/save time)
        self._config = load_yaml_file(self.config_path)

        # If the loaded config is in contracted format
        if self.expand:
            # Expand self.raw_config into self._config
            self._config = self.expand_config(self._config)

    def save(self, backup: bool = True):
        # If the loaded config was in contracted format
        if self.expand:
            # Contract self._config into self.raw_config
            save_config = self.contract_config(self._config)
        else:
            save_config = self._config
    
        if backup:
            if os.path.isfile(self.config_path):
                shutil.copyfile(self.config_path, self.config_path+".bk")

        save_yaml_file(self.config_path, save_config)

    def expand_config(self, config_dict):
        return_config = {}
        # For each value in the raw loaded config
        for key, value in config_dict.items():
            # If it's a valid expandable parameter
            if (key in self.expandable_keys and
                    type(value) is str):

                logging.debug("Expanding {}".format(value))

                # Store expansion path
                self.expandable_keys[key] = config_dict[key]
                # Create the expansion file if it doesn't yet exist
                initialise_file(value)
                # Load the expansion file into _config
                return_config[key] = load_yaml_file(value) or {}
            else:
                return_config[key] = value

        return return_config

    def contract_config(self, config_dict):
        return_config = {}
        # For each value in the expanded config
        for key, value in config_dict.items():
            # If it's a valid expandable parameter
            if (key in self.expandable_keys and
                    self.expandable_keys[key] is not None and
                    type(value) is dict):

                logging.debug("Saving to {}".format(self.expandable_keys[key]))
                # Create the file if it doesn't exist
                initialise_file(self.expandable_keys[key])
                # Save the expanded config dictionary to the file
                save_yaml_file(self.expandable_keys[key], value)
                # Replace the expanded dictionary with a file path
                return_config[key] = self.expandable_keys[key]
            else:
                return_config[key] = value

        return return_config
