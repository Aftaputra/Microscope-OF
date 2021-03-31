# OpenFlexure Microscope Software

## Quickstart

A general user-guide on setting up your microscope can be found [**here on our website**](https://www.openflexure.org/projects/microscope/).
This includes basic installation instructions suitable for most users.

Full developer documentation can be found on [**ReadTheDocs**](https://openflexure-microscope-software.readthedocs.io/). 
This includes installing the server in a mode better suited for active development.

## Key info

* Responsible for actually controlling microscope hardware, data management, and creating the API server.
Also now includes the web client, which is served from the server root.
* Server starts on port 5000 by default.
* Runs on [Python-LabThings](https://github.com/labthings/python-labthings/), and so basically all non-microscope functionality is handled by that library.

### Server settings

https://openflexure-microscope-software.readthedocs.io/en/master/config.html

There are 2 important settings files:
* `/var/openflexure/settings/microscope_configuration.json`
    * Boot-time microscope configuration. Things like the type of camera connected, the stage board, geometry etc.
    *Anything that needs to be loaded once as the server starts, and usually doesn't need to be re-written while the server is running
* `/var/openflexure/settings/microscope_settings.json`
    * Every other persistent setting. Camera settings, calibration data, default capture settings, stream resolution etc.

# Developer guidelines

## Creating releases

* Update the applications internal version number
    * Edit ``setup.py`` to update the version number
    * Git commit and git push
* Create a new version tag on GitLab (e.g. ``v2.6.11``)
    * Make sure you prefix a lower case 'v', otherwise it won't be recognised as a release!
    * This tagging will trigger a CI pipeline that builds the JS client, tarballs up the server, and deploys it
        * Note: This also updates the build server's nginx redirect map file

## Local installation

The Raspberry Pi image we use currently ships with Python 3.7.3. For local development, please use PyEnv or similar to make sure you're running on this version. For example, Windows users can use [Scoop](https://scoop.sh/) to install specific Python versions.

### Clone the repository
* `git clone https://gitlab.com/openflexure/openflexure-microscope-server.git`
* `cd openflexure-microscope-server`

### Set up the Python environment and run a test server
* (Optional) Set local Python version to match what is available on the Pi
  * `pyenv init` (this may or may not be required, depending on how you installed `pyenv`)
  * `pyenv install 3.7.3`
  * `pyenv local 3.7.3`
* Create a virtual environment and activate it:
  * `python -m venv .venv`
  * `source .venv/bin/activate` (on Linux) or `.venv/Scripts/activate` (on Windows)
  * `pip install pipenv`
  * `pipenv install --dev` (This will install development dependencies.  If you don't need these, `pipenv install` will get you just the dependencies needed to run the server, which takes about half the time.)
* Finally, run the server:
  * You can use `ofm serve` or `ofm restart` on the Raspberry Pi to manage the server.
  * To run the server locally, with dummy hardware, you can use ``python -m openflexure_microscope.api.app`` to start a development-mode Flask server on ``localhost:5000``

### Set up the Javascript environment and build
* The Flask web application, written in Python, serves a web application written in ``Vue.js``.  This is distributed as part of the built version of the server, hosted on our [build server](https://build.openflexure.org/openflexure-microscope-server/).
* You could extract the pre-built web app from this tarball, which saves you having to set up Node.js.  However, it also means you're not able to change the interface, and it's possible your interface will get out of sync with your server.
* Building the web interface will require a valid Node.js installation.  If you don't have Node.js (including ``npm``) the [Node.js website](https://nodejs.org/en/) offers downloads for all platforms, though see the instructions below for Raspberry Pi.
  * To install Node.js on a Raspberry Pi:
    * `curl -sL https://deb.nodesource.com/setup_14.x | sudo bash -`
    * `sudo apt install nodejs`
* To build the web application (this produces a set of static files, that are served by the Flask webserver)
  * `cd openflexure_microscope/api/static`
  * `npm install`
  * `npm run build`
* To create a Node.js development server (this will help various development tools to display more information, and auto-rebuilds when you change the source files) 
  * `npm run serve`
  * You access the development server on a different port (it's printed on the command line when you run the above command).  This means that when it starts up you will need to tell it where the microscope server is, using the "override API origin" field in the page that pops up.  If you are running a test server on your computer, this is most likely ``http://localhost:5000/``.

## Formatting, linting, and tests
All of the commands below assume that you are running in the OFM virtual environment, i.e. you have run ``ofm activate`` on an OpenFlexure SD card, or ``source .venv/bin/activate`` on Linux, or ``.venv/Scripts/activate``on Windows.

### Tl;dr

**Before committing**

* To auto-format the Python code run `poe format`
* To auto-format the Javascript code, run
  * ``cd openflexure_microscope/api/static``
  * ``npm run lint``

Auto-formats the code

**Before submitting a merge request/merging**

* To auto-format and type-check the Python code run `poe check`
* To auto-format the Javascript code, run
  * ``cd openflexure_microscope/api/static``
  * ``npm run lint``

Formats code, lints, runs static analysis, and runs unit tests.

### Details

We use several code analysis and formatting libraries in this project. **Please run all of these before submitting a merge request.** 

Our CI will check each of these automatically, so ensuring they pass locally will save you time.

* **Black** - Code formatting with minimal configuration.
  * While sometimes it's not perfect, its fine 90% of the time and prevents arguments about formatting. 
  * Automatically formats your code
  * This will rewrite your files in-place, so if you want to be able to revert, make a backup first!
  * `poe black`
* **Pylint** - Static code analysis
  * Analyses your code, failing if issues are detected.
  * We've disabled some less severe warnings, so _if anything fails your merge request will be blocked_
  * `poe pylint`
* **Mypy** - Type checking
  * Analyses your type hints and annotations to flag up potential bugs
  * Where possible, use type hints in your code. Even if dependencies don't support it, it'll help identify issues.
  * `poe mypy`
* **Pytest** - Unit testing
  * While unit testing is of limited use due to our dependence on real hardware, some simple isolated functions can (and should) be unit tested.
  * `poe test`

Though not in the CI, our `format` script also runs isort:

* **Isort** - Import sorting
  * Automatically organises your imports to stop things getting out of hand
  * `poe isort`

## Build-system

As of ``2.10.0b0`` we have switched to using ``pipenv`` for managing dependencies, and a standard ``setuptools`` based build system.  See "local installation" above for instructions on how to install the project.

## Changelog generation

* `npm install -g conventional-changelog-cli`
* `conventional-changelog -r 1 --config ./changelog.config.js -i CHANGELOG.md -s`

## Microscope extensions

The Microscope module, and Flask app, both support plugins for extending lower-level functionality not well suited to web API calls. The current documentation can be found [here](https://openflexure-microscope-software.readthedocs.io/en/latest/plugins.html).
