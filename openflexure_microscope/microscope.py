# -*- coding: utf-8 -*-
"""
Defines a microscope object, binding a camera and stage with basic functionality.
"""
import logging
import os
import numpy as np
import uuid

from openflexure_stage import OpenFlexureStage
from .camera.pi import StreamingCamera

from .plugins import PluginMount
from .config import load_config, save_config, convert_config


class Microscope(object):
    """
    A basic microscope object.

    The camera and stage should already be initialised, and passed as arguments.

    Args:
        camera (:py:class:`openflexure_microscope.camera.pi.StreamingCamera`): camera object
        microscope (:py:class:`openflexure_stage.stage.OpenFlexureStage`): stage object
        config (dict): Dictionary of the runtime config to apply to the microscope. Does not automatically apply to camera and stage.
        attach_plugins (bool): Should the microscope attach plugins listen in 'config' immediately.
    """
    def __init__(self, camera: StreamingCamera, stage: OpenFlexureStage, config: dict={}, attach_plugins: bool=True):

        # Attach initial hardware (may be NoneTypes)
        self.attach(camera, stage)

        # Store entire runtime-config
        self.config = config

        # Create plugin mountpoint
        self.plugin = PluginMount(self)  #: :py:class:`openflexure_microscope.plugins.PluginMount`: Mounting point for all microscope plugins

        # Attach plugins
        if attach_plugins:
            self.attach_plugins()
        
        # Get name from config, or generate
        if not 'name' in self.config:
            self.config['name'] = uuid.uuid4().hex

    def __enter__(self):
        """Create microscope on context enter."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Close microscope on context exit."""
        self.close()

    def close(self):
        """Shut down the microscope hardware."""
        if self.camera:
            self.camera.close()
        if self.stage:
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

        logging.debug("Attaching camera...")
        self.camera = camera  #: :py:class:`openflexure_microscope.camera.pi.StreamingCamera`: Picamera object
        if isinstance(self.camera, StreamingCamera):
            logging.info("Attached camera {}".format(camera))
        elif not self.camera:
            logging.info("Attached dummy camera.")

        logging.debug("Attaching stage...")
        self.stage = stage  #: :py:class:`openflexure_stage.stage.OpenFlexureStage`: OpenFlexure stage object
        if isinstance(self.stage, OpenFlexureStage):  # If a stage object has been attached
            logging.info("Attached stage {}".format(stage))
            self.stage.backlash = np.zeros(3, dtype=np.int)
        elif not self.stage:
            logging.info("Attached dummy stage.")

    def attach_plugin_maps(self, plugin_maps):
        """
        Attach plugins from a list of plugin map strings

        Args:
            plugin_maps (list): List of strings of plugin maps.
        """
        logging.debug("Attaching plugins...")

        for plugin_map in plugin_maps:
            self.plugin.attach(plugin_map)
        logging.debug("Plugins attached.")

    def attach_plugins(self):
        """
        Automatically search for plugin maps in self.config, and attach.
        """
        if 'plugins' in self.config:
            self.attach_plugin_maps(self.config['plugins'])
        else:
            logging.warning("No plugins specified in microscoperc.yaml. Skipping.")

    def reload_plugins(self):
        """
        Empty the plugin mount and re-attach from self.config.
        """
        logging.info("Tearing down existing PluginMount...")
        self.plugin = PluginMount(self)
        logging.info("Repopulating PluginMount...")
        self.attach_plugins()

    # Create unified state
    @property
    def state(self):
        """Dictionary of the basic microscope state.

        Return:
            dict: Dictionary containing position data, and :py:attr:`openflexure_microscope.camera.base.BaseCamera.state`
        """
        state = {
            'camera': {},
            'stage': {},
            'plugin': {}
        }

        # Add stage position
        position = self.stage.position
        state['stage']['position'] = {
            'x': position[0],
            'y': position[1],
            'z': position[2],
        }

        backlash = self.stage.backlash.tolist()
        state['stage']['backlash'] = {
            'x': backlash[0],
            'y': backlash[1],
            'z': backlash[2],
        }

        # Add camera state
        state['camera'] = self.camera.state

        return state
