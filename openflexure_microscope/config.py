import yaml
import os
import logging
import shutil

HERE = os.path.abspath(os.path.dirname(__file__))
DEFAULT_CONFIG_PATH = os.path.join(HERE, 'microscoperc.default.yaml')

USER_CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".openflexure")  #: str: Default path of the user-config directory, containing runtime-config and calibration files.
USER_CONFIG_FILE = os.path.join(USER_CONFIG_DIR, "microscoperc.yaml")  #: str: Default path of the user microscoperc.yaml runtime-config file.

TYPES = {
    'stream_resolution': tuple,
    'video_resolution': tuple,
    'image_resolution': tuple,
    'numpy_resolution': tuple,
    'jpeg_quality': int,
    'analog_gain': float,
    'digital_gain': float,
}  #: dict: Dictionary of expected types for common config parameters. Used by ``convert_config()``.


def convert_config(config: dict) -> dict:
    """
    Convert datatype of top-level config parameters based on the global TYPES dictionary.
    
    Args:
        config (dict): Dictionary representation of a loaded runtime-config.
    """
    global TYPES

    for key in config:
        if key in TYPES:
            config[key] = TYPES[key](config[key])

    return config


def load_config(config_path: str=None) -> dict:
    """
    Open openflexurerc.yaml runtime-config file and write to the microscope devices.

    Args:
        config_path (str): Path to the config YAML file. If `None`, defaults to `DEFAULT_CONFIG_PATH`
    """
    global DEFAULT_CONFIG_PATH, USER_CONFIG_FILE

    if not config_path:
        if os.path.exists(USER_CONFIG_FILE):  # If user config file already exists
            config_path = USER_CONFIG_FILE  # Load it
        else:  # If user config file doesn't yet exist
            logging.warning("No user config found. Loading system defaults...")
            if not os.path.exists(USER_CONFIG_DIR):
                logging.info("Making user config directory...")
                os.makedirs(USER_CONFIG_DIR)
            logging.info("Copying default config to user config...")
            shutil.copyfile(DEFAULT_CONFIG_PATH, USER_CONFIG_FILE)
            logging.info("Loading user config...")
            config_path = USER_CONFIG_FILE  # Load defaults in

    with open(config_path) as config_file:
        config_data = yaml.load(config_file)

    # Store config dictionary to self
    return convert_config(config_data)


def save_config(config_dict: dict, config_path: str=None, safe: bool=False):
    """
    Save current config dictionary to a YAML file.

    Args:
        config_dict (dict): Dictionary of config data to save.
        config_path (str): Path to the config YAML file. If `None`, defaults to `DEFAULT_CONFIG_PATH`
    """
    global USER_CONFIG_FILE
    if not config_path:
        config_path = USER_CONFIG_FILE

    with open(config_path, 'w') as outfile:
        if not safe:
            yaml.dump(config_dict, outfile)
        else:
            yaml.safe_dump(config_dict, outfile)


def merge_config(config_dict: dict, config_path: str=None, safe: bool=False, backup: bool=True):
    """
    merge current config dictionary with an existing YAML file.

    Args:
        config_dict (dict): Dictionary of config data to save.
        config_path (str): Path to the config YAML file. If `None`, defaults to `DEFAULT_CONFIG_PATH`
    """
    global USER_CONFIG_FILE
    if not config_path:
        config_path = USER_CONFIG_FILE

    config_data = load_config(config_path=config_path)

    for key, value in config_dict.items():
        config_data[key] = value

    if backup:
        if os.path.isfile(config_path):
            shutil.copyfile(config_path, config_path+".bk")

    save_config(config_data, config_path=config_path, safe=safe)
