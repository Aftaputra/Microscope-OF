import yaml
import os
import errno
import logging
import shutil
import copy

HERE = os.path.abspath(os.path.dirname(__file__))
DEFAULT_CONFIG_PATH = os.path.join(HERE, 'microscoperc.default.yaml')

USER_CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".openflexure")  #: str: Default path of the user-config directory, containing runtime-config and calibration files. Obtained from ``os.path.join(os.path.expanduser("~"), ".openflexure")``.
USER_CONFIG_FILE = os.path.join(USER_CONFIG_DIR, "microscoperc.yaml")  #: str: Default path of the user microscoperc.yaml runtime-config file. Obtained from ``os.path.join(USER_CONFIG_DIR, "microscoperc.yaml")``

with open(DEFAULT_CONFIG_PATH, 'r') as defaultrc:
    DEFAULT_CONFIG = defaultrc.read()


class OpenflexureConfig():
    expandable_keys = [
        'picamera_settings',
        'openflexure_stage_settings',
    ]  #: List of keys that can be passed as a file path string and expanded automatically

    def __init__(self, config_path: str=None, expand: bool=True):
        global DEFAULT_CONFIG, USER_CONFIG_FILE

        # Set arguments
        self.config_path = config_path or USER_CONFIG_FILE
        self.expand = expand

        # Create empty config dictionaries
        self.raw_config = {}
        # Expanded config dictionary (used by server)
        self.config = copy.copy(self.raw_config)

        # Initialise basic config file with defaults if it doesn't exist
        self.initialise_file(self.config_path, populate=DEFAULT_CONFIG)

        # Load the config in, setting self._config and self.config
        self.load()


    def update(self, update_dict: dict):
        self.config.update(update_dict)


    def overwrite(self, new_dict: dict):
        self.config = new_dict


    def load(self):
        # Unexpanded config dictionary (used at load/save time)
        self.raw_config = self.load_yaml_file(self.config_path)

        # If the loaded config is in contracted format
        if self.expand:
            # Expand self.raw_config into self._config
            self.expand_config()


    def save(self, backup: bool=True):
        # If the loaded config was in contracted format
        if self.expand:
            # Contract self._config into self.raw_config
            self.contract_config()
    
        if backup:
            if os.path.isfile(self.config_path):
                shutil.copyfile(self.config_path, self.config_path+".bk")

        self.save_yaml_file(self.config_path, self.raw_config)
        

    def expand_config(self):
        # For each value in the raw loaded config
        for key, value in self.raw_config.items():
            # If it's a valid expandable parameter
            if (key in OpenflexureConfig.expandable_keys and 
                type(value) is str):

                logging.debug("Expanding {}".format(value))
                # Initialise, load and expand
                self.initialise_file(value)
                self.config[key] = self.load_yaml_file(value) or {}
            else:
                self.config[key] = value


    def contract_config(self):
        for key, value in self.config.items():
            # If it's a valid expandable parameter
            if (key in OpenflexureConfig.expandable_keys and 
                type(value) is dict):

                # Create the file if it doesn't exist
                self.initialise_file(self.raw_config[key])
                self.save_yaml_file(self.raw_config[key], value)
            else:
                self.raw_config[key] = value


    def load_yaml_file(self, config_path) -> dict:
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


    def save_yaml_file(self, config_path: str, config_dict: dict, safe: bool=False):
        """
        Save a .yaml config file

        Args:
            config_dict (dict): Dictionary of config data to save.
            config_path (str): Path to the config YAML file. 
        """
        config_path = os.path.expanduser(config_path)

        logging.info("Saving {}...".format(config_path))

        with open(config_path, 'w') as outfile:
            if not safe:
                yaml.dump(config_dict, outfile)
            else:
                yaml.safe_dump(config_dict, outfile)


    def initialise_file(self, config_path, populate: str=""):
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
            self.create_file(config_path)
        
            logging.info("Populating {}...".format(config_path))
            with open(config_path, 'w') as outfile:
                outfile.write(populate)


    def create_file(self, config_path):
        if not os.path.exists(os.path.dirname(config_path)):
            try:
                os.makedirs(os.path.dirname(config_path))
            except OSError as exc: # Guard against race condition
                if exc.errno != errno.EEXIST:
                    raise
