import yaml
import os
import logging
import shutil

HERE = os.path.abspath(os.path.dirname(__file__))
DEFAULT_CONFIG_PATH = os.path.join(HERE, 'openflexurerc.default.yaml')
USER_CONFIG_PATH = os.path.join(os.path.expanduser("~"), "openflexurerc.yaml")

TYPES = {
    'stream_resolution': tuple,
    'video_resolution': tuple,
    'image_resolution': tuple,
    'numpy_resolution': tuple,
    'jpeg_quality': int,
    'analog_gain': float,
    'digital_gain': float,
}


def convert_config(config: dict) -> dict:
    """Convert datatype of config based on type dictionary."""
    global TYPES

    for key in config:
        if key in TYPES:
            config[key] = TYPES[key](config[key])

    return config


def load_config(config_path: str=None) -> dict:
    """
    Open openflexurerc.yaml file and write to the microscope devices.

    Args:
        config_path (str): Path to the config YAML file. If `None`, defaults to `DEFAULT_CONFIG_PATH`
    """
    global DEFAULT_CONFIG_PATH, USER_CONFIG_PATH

    if not config_path:
        if os.path.exists(USER_CONFIG_PATH):  # If user config file already exists
            config_path = USER_CONFIG_PATH  # Load it
        else:  # If user config file doesn't yet exist
            logging.warning("No user config found. Loading system defaults...")
            logging.info("Copying default config to user config...")
            shutil.copyfile(DEFAULT_CONFIG_PATH, USER_CONFIG_PATH)
            logging.info("Loading user config...")
            config_path = USER_CONFIG_PATH  # Load defaults in

    with open(config_path) as config_file:
        config_data = yaml.load(config_file)

    # Store config dictionary to self
    return convert_config(config_data)


def save_config(self, config_dict: dict, config_path: str=None):
    """
    Save current config dictionary to a YAML file.

    Args:
        config_dict (dict): Dictionary of config data to save.
        config_path (str): Path to the config YAML file. If `None`, defaults to `DEFAULT_CONFIG_PATH`
    """
    global USER_CONFIG_PATH
    if not config_path:
        config_path = USER_CONFIG_PATH

    with open(config_path, 'w') as outfile:
        yaml.dump(config_dict, outfile)
