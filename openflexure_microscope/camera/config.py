import yaml

TYPES = {
    'stream_resolution': tuple,
    'video_resolution': tuple,
    'image_resolution': tuple,
    'numpy_resolution': tuple,
    'jpeg_quality': int,
    'framerate': int,
    'awb_mode': str,
    'red_gain': float,
    'blue_gain': float,
    'shutter_speed': int,
    'saturation': int,
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


def load_config(yaml_path: str) -> dict:
    """Load YAML file, pass through dictionary conversion, and return."""
    with open(yaml_path) as config_file:
        return yaml.load(config_file)


def save_config(config: dict, yaml_path: str):
    with open('yaml_path', 'w') as outfile:
        yaml.dump(config, outfile)