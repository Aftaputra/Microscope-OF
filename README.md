OpenFlexure Microscope Software
=====================

# Installation
This module is currently in very early development, and is perhaps best installed in developer mode.
- (Recommended) create a virtual environment
    - In the openflexure-microscope-software directory, create a venv with `python3 -m venv env`
    - Activate with `source env/bin/activate`
    - Install dependencies with `sudo apt-get install libatlas-base-dev libjasper-dev libjpeg-dev`
    - Install requirements with `pip install -r requirements.txt`
- Install module in developer mode by running `python3 setup.py develop`
    - Installing in developer mode allows the module to be modified by editing files directly in the openflexure-microscope-software directory.

# Developer usage examples
## Running the web API in Gunicorn (port 5000)
- Ensure Gunicorn is installed to the current environment (`pip install gunicorn`)
- Run `gunicorn --threads 5 --workers 1 --bind 0.0.0.0:5000 openflexure_microscope.api.app:app`
    - Alternatively, run `source start_interface` from the openflexure-microscope-software directory.

## Running tests through the PTVSD remote debugger (port 3000)
- From the openflexure-microscope-software directory, run `python3 -m ptvsd --host 0.0.0.0 --port 3000 --wait tests/test_camera.py`

# REST(ish) API
The Flask app serves a (reasonably) RESTful web API. For most user-facing functionality, this is the preferred interface. 
API documentation, with example requests, is available [here](https://openflexure-microscope-software.readthedocs.io/en/latest/api.html).

# Microscope plugins
The Microscope module, and Flask app, both support plugins for extending lower-level functionality not well suited to web API calls. 
This plugin system is still in fairly early development, and is not yet properly documented. The current documentation can be found [here](https://openflexure-microscope-software.readthedocs.io/en/latest/plugins.html).

# Credits
## Video streaming
Based on supporting code for the article [video streaming with Flask](http://blog.miguelgrinberg.com/post/video-streaming-with-flask) and its follow-up [Flask Video Streaming Revisited](http://blog.miguelgrinberg.com/post/flask-video-streaming-revisited).
