Navigate pane
=============

The navigate pane displays the current stage position.  Editing the values for X, Y, and Z and then hitting "enter" or clicking "move" will move the stage to the specified coordinates.  Using the arrow keys (or page up/down) when not editing a text box will also move the stage, and the step size used can be set in the "configure" section at the top of the pane (which is collapsed by default).  Using the mouse scroll wheel on the image will also move in Z, using the same configured step size. Double clicking on the image will bring the point clicked to the centre of the field of view, if the camera-stage mapping has been calibrated (see :doc:`pane_settings`).

Autofocus can also be run from the navigate pane, by clicking the "fast", "medium" or "fine" buttons.  Fast autofocus moves the stage up and down in a continuous motion, using the size of images in the MJPEG stream from the camera to determine the sharpest point.  This is usually both faster and more accurate than the other methods, however the other two options use a different metric, and stop the stage for each measurement.  This can lead to them being more reliable in some circumstances.

.. image:: pane_navigate.png


