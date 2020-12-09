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
    * `poetry version X.y.z` (replace X.y.z with a semantic version number)
    * or `poetry version {patch/minor/major}` (see https://python-poetry.org/docs/cli/#version)
    * Git commit and git push
* Create a new version tag on GitLab (e.g. V2.6.11)
    * Make sure you prefix a lower case 'v', otherwise it won't be recognised as a release!
    * This tagging will trigger a CI pipeline that builds the JS client, tarballs up the server, and deploys it
        * Note: This also updates the build servers nginx redirect map file

## Local installation

The Raspberry Pi image we use currently ships with Python 3.7.3. For local development, please use PyEnv or similar to make sure you're running on this version. For example, Windows users can use [Scoop](https://scoop.sh/) to install specific Python versions.

* `git clone https://gitlab.com/openflexure/openflexure-microscope-server.git`
* `cd openflexure-microscope-server`
* (Optional) Set local Python version
  * `pyenv init`
  * `pyenv install 3.7.3`
  * `pyenv local 3.7.3`
* `poetry install`
  * Building the static interface will require a valid Node.js installation
  * To build on a Raspberry Pi:
    * `curl -sL https://deb.nodesource.com/setup_14.x | sudo bash -`
    * `sudo apt install nodejs`
    * `cd openflexure_microscope/api/static`
    * `npm install`
    * `npm run build`

## Formatting, linting, and tests

### Tl;dr

**Before committing**

Run `poetry run poe format`

Auto-formats the code

**Before submitting a merge request/merging**

Run `poetry run poe check`

Formats code, lints, runs static analysis, and runs unit tests.
### Details

We use several code analysis and formatting libraries in this project. **Please run all of these before submitting a merge request.** 

Our CI will check each of these automatically, so ensuring they pass locally will save you time.

* **Black** - Code formatting with minimal configuration.
  * While sometimes it's not perfect, its fine 90% of the time and prevents arguments about formatting. 
  * Automatically formats your code
  * `poetry run poe black`
* **Pylint** - Static code analysis
  * Analyses your code, failing if issues are detected.
  * We've disabled some less severe warnings, so _if anything fails your merge request will be blocked_
  * `poetry run poe pylint`
* **Mypy** - Type checking
  * Analyses your type hints and annotations to flag up potential bugs
  * Where possible, use type hints in your code. Even if dependencies don't support it, it'll help identify issues.
  * `poetry run poe mypy`
* **Pytest** - Unit testing
  * While unit testing is of limited use due to our dependence on real hardware, some simple isolated functions can (and should) be unit tested.
  * `poetry run poe test`

Though not in the CI, our `format` script also runs isort:

* **Isort** - Import sorting
  * Automatically organises your imports to stop things getting out of hand
  * `poetry run poe isort`

## Build-system

As of 1.0.0b0, we're using [Poetry](https://github.com/sdispater/poetry) to manage dependencies, build, and distribute the package. All package information and dependencies are found in `pyproject.toml`, in line with [PEP 518](https://www.python.org/dev/peps/pep-0518/). If you're developing this package, make use of `poetry.lock` to ensure you're using the latest locked dependency list.

## Changelog generation

* `npm install -g conventional-changelog-cli`
* `conventional-changelog -r 1 --config ./changelog.config.js -i CHANGELOG.md -s`

## Microscope extensions

The Microscope module, and Flask app, both support plugins for extending lower-level functionality not well suited to web API calls. The current documentation can be found [here](https://openflexure-microscope-software.readthedocs.io/en/latest/plugins.html).
