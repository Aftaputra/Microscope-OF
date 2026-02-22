"""A package for all of the core LabThings-FastAPI Things shipped with the microscope.

The microscope can be extended to be used with other hardware by creating a package
with other Things and including them in the LabThings-FastAPI config file.
"""

import posixpath
from typing import Optional, Self

from starlette.routing import Mount
from starlette.staticfiles import StaticFiles

import labthings_fastapi as lt


class OFMThing(lt.Thing):
    """A custom LabThings Thing class for the OpenFlexure Microscope."""

    _data_dir: Optional[str] = None

    def __enter__(self) -> Self:
        """Set the data directory when the Thing is entered."""
        self._data_dir = get_data_directory_from_server(self)
        return self

    @property
    def data_dir(self) -> str:
        """The data directory for this thing."""
        if self._data_dir is None:
            raise RuntimeError(
                "No data directory set. Has the LabThings server been started?"
            )
        return self._data_dir


def get_data_directory_from_server(thing: lt.Thing) -> str:
    """Get the data directory from the server.

    :param thing: The Thing to get the data directory for.

    :return: The data directory as a string:
    :raise RuntimeError: If not able to get the data directory for any reason.
    """
    server = thing._thing_server_interface._server()
    if server is None:
        raise RuntimeError("No server found to communicate with.")
    routes = server.app.routes
    try:
        route_paths = [route.path if hasattr(route, "path") else "" for route in routes]
        data_index = route_paths.index("/data")
    except ValueError as e:
        raise RuntimeError("Could not find data directory") from e
    mount = routes[data_index]
    if not isinstance(mount, Mount):
        raise RuntimeError("Data directory isn't a starlette.routing.Mount.")
    if not isinstance(mount.app, StaticFiles):
        raise RuntimeError("Data is not mounted as static files.")
    app_data_dir = mount.app.directory
    if app_data_dir is None:
        raise RuntimeError("Data directory is not set.")
    return posixpath.join(str(app_data_dir), thing.path.strip("/"))
