# -*- coding: utf-8 -*-
"""
Defines a microscope object, binding a camera and stage with basic functionality.
"""
import logging
import os
import numpy as np

from openflexure_stage import OpenFlexureStage
from .camera.pi import StreamingCamera

from .plugins import PluginMount, load_plugin, search_plugin_dirs
from .config import load_config, save_config, convert_config


class Microscope(object):
    """
    A basic microscope object.

    The camera and stage should already be initialised, and passed as arguments.

    Args:
        camera (:py:class:`openflexure_microscope.camera.pi.StreamingCamera`): camera object
        microscope (:py:class:`openflexure_stage.stage.OpenFlexureStage`): stage object
        load_config (bool): Should a config file be automatically loaded on init?
        config_path (str): Path to the config YAML file to be loaded. If None, defaults to USER_CONFIG_PATH.
    """
    def __init__(self, camera: StreamingCamera, stage: OpenFlexureStage):

        self.attach(camera, stage)

        # Create plugin mountpoint
        self.plugin = PluginMount(self)  #: :py:class:`openflexure_microscope.plugins.PluginMount`: Mounting point for all microscope plugins

    def __enter__(self):
        """Create microscope on context enter."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Close microscope on context exit."""
        self.close()

    def close(self):
        """Shut down the microscope hardware."""
        self.camera.close()
        self.stage.close()

    def attach(self, camera: StreamingCamera, stage: OpenFlexureStage, apply_config: bool=True):
        """
        Retroactively attaches a camera and stage to the microscope object.

        Allows the microscope to be created as a "dummy", with hardware communications
        opened at a later time.

        Args:
            camera (:py:class:`openflexure_microscope.camera.pi.StreamingCamera`): camera object
            microscope (:py:class:`openflexure_stage.stage.OpenFlexureStage`): stage object
            apply_config (bool): Should the microscope config dictionary be applied to the attached hardware?
        """

        self.camera = camera  #: :py:class:`openflexure_microscope.camera.pi.StreamingCamera`: Picamera object
        if isinstance(camera, StreamingCamera):
            logging.info("Attached camera {}".format(camera))

        self.stage = stage  #: :py:class:`openflexure_stage.stage.OpenFlexureStage`: OpenFlexure stage object
        if isinstance(self.stage, OpenFlexureStage):  # If a stage object has been attached
            logging.info("Attached stage {}".format(stage))
            self.stage.backlash = np.zeros(3, dtype=np.int)

    def find_plugins(self, plugin_paths=[], include_default=True):
        """
        Automatically search for plugins, and attach to self.

        Args:
            plugin_paths (list): List of strings of plugin directories.
            include_default (bool): Also load plugins from the module default directory (DEFAULT_PLUGIN_PATH)
        """
        # TODO: Get paths from rc file
        plugins_list = search_plugin_dirs(plugin_paths, include_default=include_default)

        for i in plugins_list:
            module = load_plugin(i)
            self.plugin.attach(module)

    # Create unified state
    @property
    def state(self):
        """Dictionary of the basic microscope state.

        Return:
            dict: Dictionary containing position data, and :py:attr:`openflexure_microscope.camera.base.BaseCamera.state`
        """
        state = {}

        # Add stage position
        position = self.stage.position
        state['position'] = {
            'x': position[0],
            'y': position[1],
            'z': position[2],
        }

        # Add camera state
        state.update(self.camera.state)

        return state
