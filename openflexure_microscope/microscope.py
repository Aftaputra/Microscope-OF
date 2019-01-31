# -*- coding: utf-8 -*-
"""
Defines a microscope object, binding a camera and stage with basic functionality.
"""
import logging
import numpy as np
import uuid

from openflexure_stage import OpenFlexureStage
from .camera.pi import StreamingCamera

from .plugins import PluginMount
from .utilities import axes_to_array
from .task import TaskOrchestrator
from .lock import CompositeLock
from .config import OpenflexureConfig


class Microscope(object):
    """
    A basic microscope object.

    The camera and stage should already be initialised, and passed as arguments.

    Args:
        camera (:py:class:`openflexure_microscope.camera.pi.StreamingCamera`): camera object
        stage (:py:class:`openflexure_stage.stage.OpenFlexureStage`): stage object
        config_path (str): Path to a microscoperc.yaml runtime-config file
        attach_plugins (bool): Should the microscope attach plugins listen in 'config' immediately.
    """
    def __init__(
            self,
            camera: StreamingCamera,
            stage: OpenFlexureStage,
            config_path: str = None,
            attach_plugins: bool = True):

        # Create RC object
        self.rc = OpenflexureConfig(config_path=config_path, expand=True)

        # Attach initial hardware (may be NoneTypes)
        self.camera = None
        self.stage = None
        self.attach(camera, stage)

        # Create a task orchestrator
        self.task = TaskOrchestrator()  #: :py:class:`openflexure_microscope.task.TaskOrchestrator`: Threaded task orchestrator

        # Create plugin mount-point
        self.plugin = PluginMount(self)  #: :py:class:`openflexure_microscope.plugins.PluginMount`: Mounting point for all microscope plugins

        # Attach plugins
        if attach_plugins:
            self.attach_plugins()
        
        # Set default parameters
        if 'name' not in self.rc.config:
            self.rc.write({'name': uuid.uuid4().hex})
        
        if 'fov' not in self.rc.config:
            self.rc.write({'fov': [0, 0]})
        
        # Initialise with an empty composite lock
        self.lock = CompositeLock([])  #: :py:class:`openflexure_microscope.lock.CompositeLock`: Composite lock controlling thread access to multiple pieces of hardware

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

    def attach(self, camera: StreamingCamera, stage: OpenFlexureStage):
        """
        Retroactively attaches a camera and stage to the microscope object.

        Allows the microscope to be created as a "dummy", with hardware communications
        opened at a later time.

        Args:
            camera (:py:class:`openflexure_microscope.camera.pi.StreamingCamera`): camera object
            stage (:py:class:`openflexure_stage.stage.OpenFlexureStage`): stage object
        """

        logging.debug("Attaching camera...")
        self.camera = camera  #: :py:class:`openflexure_microscope.camera.pi.StreamingCamera`: Picamera object
        if isinstance(self.camera, StreamingCamera):
            logging.info("Attached camera {}".format(camera))
            logging.info("Updating camera settings")
            self.write_config(self.camera.read_config())
        elif not self.camera:
            logging.info("Attached dummy camera.")
        # If camera has a lock
        if hasattr(self.camera, 'lock'):
            logging.info("Attaching {} to composite lock.".format(self.camera.lock))
            # Add the lock to the microscope composite lock
            self.lock.locks.append(self.camera.lock)

        logging.debug("Attaching stage...")
        self.stage = stage  #: :py:class:`openflexure_stage.stage.OpenFlexureStage`: OpenFlexure stage object
        if isinstance(self.stage, OpenFlexureStage):  # If a stage object has been attached
            logging.info("Attached stage {}".format(stage))
            self.stage.backlash = np.zeros(3, dtype=np.int)
        elif not self.stage:
            logging.info("Attached dummy stage.")
        # If stage object has a lock
        if hasattr(self.stage, 'lock'):
            logging.info("Attaching lock {} to composite lock.".format(self.stage.lock))
            # Add the lock to the microscope composite lock
            self.lock.locks.append(self.stage.lock)

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
        if 'plugins' in self.rc.config:
            self.attach_plugin_maps(self.rc.config['plugins'])
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
        if self.stage:  # If stage exists, populate with real values
            position = self.stage.position
        else:  # Else, zero
            position = [0, 0, 0]

        state['stage']['position'] = {
            'x': position[0],
            'y': position[1],
            'z': position[2],
        }

        # Add camera state
        state['camera'] = self.camera.state

        return state

    def write_config(self, config: dict):
        """
        Writes  and applies a config dictionary. Missing parameters will be left untouched.
        """
        # If attached to a camera
        if self.camera:
            # Update camera config
            self.camera.config = config

        # If attached to a stage
        # TODO: Convert stage settings into a config expansion
        if self.stage:
            if 'backlash' in config:
                # Construct backlash array
                backlash = axes_to_array(config['backlash'], ['x', 'y', 'z'], [0, 0, 0])
                self.stage.backlash = backlash

        # Cache config
        self.rc.write(config)

    def read_config(self, json_safe=False):
        """
        Read an updated config including camera settings.
        """
        # If attached to a camera
        if self.camera:
            # Update camera config params from StreamingCamera object
            self.rc.write(self.camera.read_config())

        # If attached to a stage
        if self.stage:
            backlash = self.stage.backlash.tolist()
        else:
            backlash = [0, 0, 0]

        backlash = {
            'backlash': {
                'x': backlash[0],
                'y': backlash[1],
                'z': backlash[2],
            }
        }

        self.rc.write(backlash)

        return self.rc.read(json_safe=json_safe)

    def save_config(self):
        """
        Saves the current runtime-config back to disk
        """
        # Get any changed device settings
        self.read_config()
        # Save to disk
        self.rc.save()

    @property
    def config(self) -> dict:
        return self.read_config()

    @config.setter
    def config(self, config: dict) -> None:
        self.write_config(config)
