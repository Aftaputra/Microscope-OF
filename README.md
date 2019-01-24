OpenFlexure Microscope Software
=====================

# Installation
- (Recommended) create a virtual environment
    - Create a virtual environment with `python3 -m venv env` (or your favourite virtual environment system)
    - Activate with `source env/bin/activate`
- Install non-python dependencies with `sudo apt-get install libatlas-base-dev libjasper-dev libjpeg-dev`
- Install module by running `pip install openflexure-microscope==1.0.0b5`


# Usage
## Running the web API in Gunicorn (port 5000)
- Ensure Gunicorn is installed to the current environment (`pip install gunicorn`)
- Run `gunicorn --threads 5 --workers 1 --bind 0.0.0.0:5000 openflexure_microscope.api.app:app`

# REST(ish) API
The Flask app serves a (reasonably) RESTful web API. For most user-facing functionality, this is the preferred interface. 
API documentation, with example requests, is available [here](https://openflexure-microscope-software.readthedocs.io/en/latest/api.html).


# Developer notes

## Build-system
As of 1.0.0b0, we're using [Poetry](https://github.com/sdispater/poetry) to manage dependencies, build, and distribute the package. All package information and dependencies are found in `pyproject.toml`, in line with [PEP 518](https://www.python.org/dev/peps/pep-0518/). If you're developing this package, make use of `poetry.lock` to ensure you're using the latest locked dependency list.

## Microscope plugins
The Microscope module, and Flask app, both support plugins for extending lower-level functionality not well suited to web API calls. 
This plugin system is still in fairly early development, and is not yet properly documented. The current documentation can be found [here](https://openflexure-microscope-software.readthedocs.io/en/latest/plugins.html).

## Running tests through the PTVSD remote debugger (port 3000)
- From the openflexure-microscope-software directory, run `python3 -m ptvsd --host 0.0.0.0 --port 3000 --wait tests/test_camera.py`


# Credits
## Video streaming
Based on supporting code for the article [video streaming with Flask](http://blog.miguelgrinberg.com/post/video-streaming-with-flask) and its follow-up [Flask Video Streaming Revisited](http://blog.miguelgrinberg.com/post/flask-video-streaming-revisited).
