import yaml
import os
import errno
import logging
import shutil

HERE = os.path.abspath(os.path.dirname(__file__))
DEFAULT_CONFIG_PATH = os.path.join(HERE, 'microscoperc.default.yaml')

USER_CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".openflexure")  #: str: Default path of the user-config directory, containing runtime-config and calibration files. Obtained from ``os.path.join(os.path.expanduser("~"), ".openflexure")``.
USER_CONFIG_FILE = os.path.join(USER_CONFIG_DIR, "microscoperc.yaml")  #: str: Default path of the user microscoperc.yaml runtime-config file. Obtained from ``os.path.join(USER_CONFIG_DIR, "microscoperc.yaml")``

with open(DEFAULT_CONFIG_PATH, 'r') as default_rc:
    DEFAULT_CONFIG = default_rc.read()


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
        return self._config

    def asdict(self):
        return self._config

    def update(self, update_dict: dict):
        self._config.update(update_dict)

    def overwrite(self, new_dict: dict):
        self._config = new_dict

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

                logging.debug("Saving to {}:".format(self.expandable_keys[key]))
                logging.debug(value)
                # Create the file if it doesn't exist
                initialise_file(self.expandable_keys[key])
                # Save the expanded config dictionary to the file
                save_yaml_file(self.expandable_keys[key], value)
                # Replace the expanded dictionary with a file path
                return_config[key] = self.expandable_keys[key]
            else:
                return_config[key] = value

        return return_config
