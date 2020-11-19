# OpenFlexure Microscope Software

## Quickstart

A general user-guide on setting up your microscope can be found [**here on our website**](https://www.openflexure.org/projects/microscope/).
This includes basic installation instructions suitable for most users.

Full developer documentation can be found on [**ReadTheDocs**](https://openflexure-microscope-software.readthedocs.io/). 
This includes installing the server in a mode better suited for active development.

# Developer guidelines

## Installation

* `git clone https://gitlab.com/openflexure/openflexure-microscope-server.git`
* `poetry install`
* `poetry run build_static`
  * Building the static interface will require a valid Node.js installation
  * To build on a Raspberry Pi:
    * `curl -sL https://deb.nodesource.com/setup_14.x | sudo bash -`
    * `sudo apt install nodejs`

## Formatting and linting

We use 3 main code analysis and formatting libraries in this project. **Please run all of these before submitting a merge request.** 

Our CI will check each of these automatically, so ensuring they pass locally will save you time.

* **Black** - Code formatting with minimal configuration.
  * While sometimes it's not perfect, its fine 90% of the time and prevents arguments about formatting. 
  * Automatically formats your code
  * `poetry run black .`
* **Isort** - Import sorting
  * Automatically organises your imports to stop things getting out of hand
  * `poetry run isort .`
* **Pylint** - Static code analysis
  * Analyses your code, failing if issues are detected.
  * We've disabled some less severe warnings, so _if anything fails your merge request will be blocked_
  * `poetry run pylint openflexure_microscope`

### Pre-commit hooks

We support pre-commit hooks to run code formatting before committing to the codebase.

The simplest way to ensure this works is to install pre-commits into your current Python environment:

* `pip3 install pre-commit`
* `pre-commit install`

To run pre-commit analysis manually, you can run `pre-commit run`.


## Build-system

As of 1.0.0b0, we're using [Poetry](https://github.com/sdispater/poetry) to manage dependencies, build, and distribute the package. All package information and dependencies are found in `pyproject.toml`, in line with [PEP 518](https://www.python.org/dev/peps/pep-0518/). If you're developing this package, make use of `poetry.lock` to ensure you're using the latest locked dependency list.

## Microscope extensions

The Microscope module, and Flask app, both support plugins for extending lower-level functionality not well suited to web API calls. The current documentation can be found [here](https://openflexure-microscope-software.readthedocs.io/en/latest/plugins.html).

# Credits

## Piexif

The microscope server includes a forked copy of hMatoba's [Piexif](https://github.com/hMatoba/Piexif), licensed under the MIT License.

## Video streaming

Camera streaming was initially based on supporting code for the article [video streaming with Flask](http://blog.miguelgrinberg.com/post/video-streaming-with-flask) and its follow-up [Flask Video Streaming Revisited](http://blog.miguelgrinberg.com/post/flask-video-streaming-revisited).
