Quickstart
=======================================================

Install
-------

Quick-installer
+++++++++++++++
For most users, this is the reccommended installation method.

- Run ``curl -LSs get.openflexure.org/microscope |sudo bash``
    - See the `GitLab repo <https://gitlab.com/openflexure/openflexure-microscope-installer>`_ for details.
- Follow on-screen prompts

Really-quick installer
^^^^^^^^^^^^^^^^^^^^^^
The installer script can run with all default settings applied, removing all user prompts.

- Run ``curl -LSs get.openflexure.org/microscope |sudo bash -s -- -y``

Developer installer
^^^^^^^^^^^^^^^^^^^
The installer script can pull the latest development package from our git repository, and use install into a developer environment using Poetry.

- Run ``curl -LSs get.openflexure.org/microscope |sudo bash -s -- -d``


Manual installation
+++++++++++++++++++
- (Recommended) create a virtual environment
    - ``pip3 install virtualenv``
    - ``mkdir ~/.openflexure``
    - ``python3 -m virtualenv ~/.openflexure/envmicroscope``
    - Activate with ``source /.openflexure/envmicroscope/bin/activate``
- Install non-python dependencies with ``sudo apt-get install libatlas-base-dev libjasper-dev libjpeg-dev``
- **Users:** Install module by running ``pip install openflexure-microscope``
- **Developers:** Install `Poetry <https://github.com/sdispater/poetry>`_, clone this repo, and ``poetry install`` from inside the repo.

API Server
----------

If you use the auto-installer, a system.d service will be generated automatically, and you will be prompted to enable it at startup.
The service can be controlled with the following commands:

===================  ====
**Start**            ``sudo systemctl start ofmserver``
**Stop**             ``sudo systemctl stop ofmserver``
**Restart**          ``sudo systemctl restart ofmserver``
**Check status**     ``sudo systemctl status ofmserver``
**Disable on-boot**  ``sudo systemctl disable ofmserver``
**Enable on-boot**   ``sudo systemctl enable ofmserver``
===================  ====

Manually starting the server with Gunicorn
++++++++++++++++++++++++++++++++++++++++++

This can be especially useful for developers, giving more immediate feedback on the status of the server.

- Ensure Gunicorn is installed to the current environment (``pip install gunicorn``)
- Run ``gunicorn --threads 5 --workers 1 --graceful-timeout 3 --bind 0.0.0.0:5000 openflexure_microscope.api.app:app``
    - We spawn 5 threads to handle simultaneous connections
    - We spawn a single worker as only one process can access the Pi camera simultaneously
    - We shorten the graceful-timeout to 3 seconds, to avoid stalling if a camera feed connection is active
    - Binding to 0.0.0.0:5000 opens the server up on port 5000 to devices outside of localhost