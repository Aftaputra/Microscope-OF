Microscope configuration
=======================================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

.. _MicroscopeRC:

Microscope RC file
------------------

Example
+++++++
.. code-block:: python

    from openflexure_microscope import Microscope, config
    from openflexure_microscope.camera.pi import StreamingCamera
    from openflexure_stage import OpenFlexureStage

    # Load default user config from ~/.openflexure/microscoperc.yaml
    openflexurerc = config.load_config()  

    # Create a picamera StreamingCamera, using our config
    camera_obj = StreamingCamera(config=openflexurerc)

    # Create an OpenFlexure Stage attached to /dev/ttyUSB0
    stage_obj = OpenFlexureStage("/dev/ttyUSB0")  
    
    # Attach devices and config to a Microscope object
    api_microscope = Microscope(camera_obj, stage_obj, config=openflexurerc) 

Default microscoperc.yaml
+++++++++++++++++++++++++
.. code-block:: yaml

    # The analog gain offers higher sensitivity and less noise than using digital gain only
    analog_gain: 1.
    digital_gain: 1.

    # Resolutions for streaming and capture
    video_resolution: [832, 624]
    image_resolution: [2592, 1944]
    numpy_resolution: [1312, 976]

    # Capture quality
    jpeg_quality: 75

    # Parameters specific to PiCamera objects
    picamera_params:
      exposure_mode: 'off'
      awb_mode: 'off'
      awb_gains: [0.9, 2.8]
      framerate: 24
      shutter_speed: 30000
      saturation: 0
      led: false

    # Default plugins
    plugins:
    - openflexure_microscope.plugins.default:Plugin

Config module
-------------
.. automodule:: openflexure_microscope.config
    :members: