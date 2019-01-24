Quickstart
=======================================================

Install
-------
- (Recommended) create a virtual environment
    - Create a virtual environment with ``python3 -m venv env`` (or your favourite virtual environment system)
    - Activate with ``source env/bin/activate``
- Install non-python dependencies with ``sudo apt-get install libatlas-base-dev libjasper-dev libjpeg-dev``
- Install module by running ``pip install openflexure-microscope==1.0.0b5``

Web API
-------

Simple development server with Gunicorn
+++++++++++++++++++++++++++++++++++++++

- Ensure Gunicorn is installed to the current environment (``pip install gunicorn``)
- Run ``gunicorn --threads 5 --workers 1 --bind 0.0.0.0:5000 openflexure_microscope.api.app:app``