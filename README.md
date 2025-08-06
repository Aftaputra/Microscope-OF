# OpenFlexure Microscope Software

> ## This is the v3 development branch
> We are no longer actively developing v2, but v3 is not yet released.
> v3 is not yet stable enough for wider public release. Development snapshots are released from time to time.
> If you want to use a development snapshot before we do a wider alpha release the best thing to do is get in contact on the [forum](https://openflexure.discourse.group/).
 If you want to look at the code for v2 you should look at the [master branch](https://gitlab.com/openflexure/openflexure-microscope-server/-/tree/master).


The "server" is the main component of the OpenFlexure Microscope's software.  It is responsible for controlling microscope hardware, data management, and allowing it to be controlled locally and over a network.
This repository includes the graphical interface, which is implemented as a web application served from the root of the Python web server. The simplest way to use it is via OpenFlexure eV, which should find your microscope on the network, and display the interface. The microscope's interface can also be accessed at `http://microscope.local:5000/` in a web browser, assuming the hostname of your microscope is `microscope`.

This software runs on [LabThings-FastAPI](https://github.com/labthings/labthings-fastapi/), which creates an HTTP server using FastAPI (which in turn relies on Starlette and pydantic).

## Getting started

A general user-guide on setting up your microscope can be found [**here on our website**](https://www.openflexure.org/projects/microscope/).
This includes basic installation instructions suitable for most users.
The simplest way to set up a microscope is to download the pre-built Raspberry Pi SD card image, which has this server already installed, along with all of its dependencies.
There are instructions on how to [use the microscope](https://openflexure.org/projects/microscope/control) once you have installed the software, either from OpenFlexure Connect, or through a web browser.
The web server starts on port 5000 by default, and the microscope SD image uses the hostname "microscope" so you can usually access the web interface at <http://microscope.local:5000/>.

A user guide and developer documentation **for v2 of the server** can be found on [**ReadTheDocs**](https://openflexure-microscope-software.readthedocs.io/), including some installation notes, a link to the HTTP API reference, and guidance for developing extensions.
More information is also available in the [handbook](https://gitlab.com/openflexure/microscope-handbook/), and in the "development instructions" below.

## Running directly

The Python package provides a command `ofm-microscope-server` that runs the server. This is what is used by `systemd` to run the service. You will need to provide some command-line arguments, see the output of `--help` for an up to date list. See `/etc/systemd/system/openflexure-microscope-server.service` for the command line used to run the server by default on the  Raspberry Pi. In general, you are likely to want to specify a configuration file with `-c`, a host (`--host 0.0.0.0` to serve on all addresses) and a port (`--port 5000`). The `--fallback` option will allow the server to start *even if the hardware specified in the configuration file can't load*. This serves an error page, rather than have the server fail. In the future, it should redirect users to a way to fix their configuration.

It is also possible to run the server in simulation mode. See Developer guidelines below.

## Settings

The microscope is initially configured by a LabThings config file. This specifies two important things:

* The Python classes (and initialisation arguments) to use for each `Thing`. This sets the type of camera and stage, and enables/disables additional functionality like scanning and autofocus.
* The location of the settings folder, where each Thing can store its settings.

By default, this configuration file should be read from `/var/openflexure/settings/ofm_config.json` when the microscope is run as a service. If it is run at the command line you should specify the configuration using the `-c` command line flag. This configuration file does not change often, and usually only needs to be updated when you change the physical hardware. It may be that this file should be made read-only, particularly in microscopes deployed for e.g. medical applications.

The settings folder is, by default, `/var/openflexure/settings/` on the SD card, or `./settings/` if run elsewhere. It can be changed in the configuration file. This holds every other persistent setting. Camera settings, calibration data, default capture settings, stream resolution and so on. There is one folder per `Thing`, each with their own file. The settings files can change very regularly, and if you need to reset your settings, it's usually these files that you should remove or reset. If you delete one settings file this should reset the corresponding `Thing`, you don't have to delete the whole folder.

# Developer guidelines

## Installation and set up

To set up a development environment you will need Python 3.11 and the static files for the web application.

### Installation and set up on a Raspberry Pi

Python 3.11 should come with the OpenFlexure Raspberry Pi OS image. We do not recommend trying to develop on a standard OS image.


* To activate the microscope virtual environment run `ofm activate`
* Navigate to the Openflexure repository with `cd /var/openflexure/application/openflexure-microscope-server`

The Pi should aready come with the static files for the web application.

### Installation and set up on other platforms

You should install Python 3.11. If you have a different version of python we recommend using [UV](https://docs.astral.sh/uv/) to set up a Python 3.11 virtual environment.

* Clone the source code: `git clone https://gitlab.com/openflexure/openflexure-microscope-server.git`
* Enter the directory `cd openflexure-microscope-server`
* Create the virtual environment, for example with `uv venv --python 3.11`
* Activate your virtual environment with `source .venv/bin/activate` (on Linux) or `.venv\Scripts\activate.bat` (on Windows)
* Install the application `uv pip install -e .[dev]` (or `pip install -e .[dev]` if you are not using UV)
* Run `python pull_webapp.py` to get the latest static files for the web application.

## Running the server

### Running the server on a Raspberry Pi

You can manage the server with the `ofm` command, using `ofm start`, `ofm stop`, and `ofm restart` to do the respective actions. Often, stopping the server and running it manually will make errors easier to spot. To do this, run:
```
ofm stop
ofm activate
cd /var/openflexure
sudo -u openflexure-ws openflexure-microscope-server --fallback -c microscope_configuration.json --host 0.0.0.0 --port 5000
```

### Running the simulation server on other platforms

To start the simulation server:

* Activate the virtual environment that was set up during installation
* Run:

    openflexure-microscope-server --fallback -c ./ofm_config_simulation.json


## General development overview

Please first read our **[project contributions guide](./CONTRIBUTING.md)**

* We recommend all development is done on a branch.
* If you are editing the web app please see our see the README in the [webapp](./webapp) directory.
* If you want to try a branch that with webapp changes and don't want to copile the javascript run `python pull_webapp.py -b <branch_name>` to get the artifacts from the GitLab CI.

**For development on a Raspberry Pi** we recommend VSCode Remote session from another computer.  This allows you to use your usual developer environment to write code, but everything runs on the Raspberry Pi with real hardware.  Note that the repository is cloned by default over `https`, so you will probably need to change the "remote" URL to your fork of the repository, or to SSH, before you're able to push changes.

### Adding functionality

The microscope comprises a number of `Thing` instances, which provide actions and properties to implement hardware control and software features. These may be imported from any Python module, using `ofm_config.json`. See the LabThings-FastAPI documentation for how to create a `Thing`. 

Currently, the camera and stage classes are provided by external libraries, `labthings-picamera2` and `labthings-sangaboard`. Replacing these is the easiest way to use alternative hardware: interfaces are defined in `openflexure_microscope_server.things.camera` and `openflexure_microscope_server.things.stage` respectively.


### Python: Formatting, linting, and tests

All of the commands below assume that you are running in the OFM virtual environment, i.e. you have run `ofm activate` on an OpenFlexure SD card, or `source .venv/bin/activate` on Linux, or `.venv/Scripts/activate`on Windows.

**Before committing** you should lint and auto-format your code:

* To lint run `ruff check`
* To auto-format the Python code run `ruff format`
* To auto-format the Javascript code, run
  * `cd webapp`
  * `npm run lint`

**Before merging** please auto-format your code and also run the quality checks (linting, static analysis, and unit tests)

* All commands above
* `pytest`


We use several code analysis and formatting libraries in this project. Our CI will check each of these automatically, so ensuring they pass locally will save you time. Currently `ruff` is used for linting/formatting and `pytest` for unit tests. `mypy` will be enabled once the codebase is ready.

### Python environment, build, and dependencies

As of `v3` we specify dependencies in `pyproject.toml`. These are not currently frozen due to difficulties matching versions on different platforms. On Raspberry Pi, it's best to specify `--only-binary=:all:` to ensure libraries like `numpy` and `scipy` are not compiled from source (which takes many hours, and/or fails). Pinning dependencies with `requirements.txt` and/or `requirements.in` may happen in the future.


# Notes for Maintainers

## Creating releases

* Update the application's internal version number
  * Edit `pyproject.toml` to update the version number
* Update the changelog
* Git commit and git push
* Create a new version tag on GitLab (e.g. `v2.6.11`) that matches the `pyproject.toml` version number.
    * Make sure you prefix a lower case 'v', otherwise it won't be recognised as a release!
    * This tagging will trigger a CI pipeline that builds the JS client, tarballs up the server, and deploys it
        * Note: This also updates the build server's nginx redirect map file

## Changelog generation

* `npm install -g conventional-changelog-cli`
* `npx conventional-changelog -r 1 --config ./changelog.config.js -i CHANGELOG.md -s`
