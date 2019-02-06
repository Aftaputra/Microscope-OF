Capture Object
=======================================================

By default, all image and video capture data are stored to instances of :py:class:`openflexure_microscope.camera.capture.CaptureObject`. This class mostly wraps up complexity associated with moving data between disk and memory. The class also includes some convenience features such as automatically cleaning up captures marked as temporary, handling metadata files and file names, and generating image thumbnails. Often, the most recent capture wants to be store din memory, for applications that involve immediately processing the capture data in some way. Rather than manually keep track of the location of the capture data, you can use the CaptureObject ``data`` attribute, which automatically returns capture data from the fastest available location. Below are details of available methods and attributes.

.. automodule:: openflexure_microscope.camera.capture
    :members: