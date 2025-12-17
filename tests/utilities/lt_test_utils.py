"""Test utilities for interacting with the labthings Server."""

import tempfile
import time
from types import TracebackType
from typing import Any, Optional, Self

import requests
from fastapi.testclient import TestClient

import labthings_fastapi as lt

ACTION_RUNNING_KEYWORDS = ["idle", "pending", "running"]


class LabThingsTestEnv:
    """A Labthings Server running in a FastAPI Test Client.

    This can be used to create ThingClients for testing, to to enable direct access to
    the server, or things on the server. It also provides high level functions to
    start actions without blocking the test thread.

    Use this as a context manager:

    .. code-block:: python

        with LabThingsTestEnv(things={"counter", CountingThing}) as env:
            ...
    """

    def __init__(
        self, things: dict[str, lt.Thing | str], settings_folder: Optional[str] = None
    ) -> None:
        """Initialise the test environment.

        The server and FastAPI TestClient are server are not created until this is used
        as a context manager:

        :param things: The thing configuration dictionary used to initialise the server.
        :param settings_folder: The settings folder to use.
        """
        self._server: Optional[lt.ThingServer]
        self._test_client: Optional[TestClient]
        self._thing_config = things
        self._settings_folder = settings_folder
        self._tmp_dir_obj: Optional[tempfile.TemporaryDirectory] = None

    def __enter__(self) -> Self:
        """Create server and run it in the TestClient."""
        if self._settings_folder is None:
            self._tmp_dir_obj = tempfile.TemporaryDirectory()
            self._settings_folder = self._tmp_dir_obj.name
        self._server = lt.ThingServer(
            things=self._thing_config, settings_folder=self._settings_folder
        )
        self._test_client = TestClient(self._server.app)
        self._test_client.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        """Close the TestClient and cleanup."""
        self._test_client.__exit__(exc_type, exc_value, traceback)
        if self._tmp_dir_obj is not None:
            self._tmp_dir_obj.cleanup()

    @property
    def server(self) -> lt.ThingServer:
        """The LabThings Server."""
        if self._server is None:
            raise RuntimeError("No server was started.")
        return self._server

    @property
    def client(self) -> TestClient:
        """The FastAPI TestClient running the server."""
        if self._test_client is None:
            raise RuntimeError("No server was started.")
        return self._test_client

    def check_thing_exists(self, thing_name: str):
        """Raise a ValueError if no thing of with a matching name exists."""
        if thing_name not in self.server.things:
            raise ValueError(f"No Thing named {thing_name}")

    def get_thing(self, thing_name: str) -> lt.Thing:
        """Get a Thing from the server by name."""
        self.check_thing_exists(thing_name)
        return self.server.things[thing_name]

    def get_thing_client(self, thing_name: str) -> lt.ThingClient:
        """Get a ThingClient for a Thing by name."""
        self.check_thing_exists(thing_name)
        thing = self.server.things[thing_name]
        return lt.ThingClient.from_url(thing.path, self.client)

    def start_action(
        self,
        thing_name: str,
        action_name: str,
        action_kwargs: Optional[dict[str, Any]] = None,
    ) -> requests.Response:
        """Start an action and return the server response.

        This response can be used to poll or cancel the action.
        """
        self.check_thing_exists(thing_name)
        url = f"/{thing_name}/{action_name}"
        json_payload = {} if action_kwargs is None else action_kwargs
        response = self.client.post(url, json=json_payload)
        response.raise_for_status()
        return response

    def poll_action(
        self, response: requests.Response, interval: float = 0.01
    ) -> dict[str, Any]:
        """Poll an action until it completes and return the final response data."""
        invocation_data = response.json()

        if "status" not in invocation_data:
            raise ValueError(f"Response json has no status: {invocation_data}")
        first_run = True
        while invocation_data["status"] in ACTION_RUNNING_KEYWORDS:
            if first_run:
                first_run = False
            else:
                time.sleep(interval)
            response = self.client.get(_invocation_href(invocation_data))
            response.raise_for_status()
            invocation_data = response.json()
        return invocation_data

    def cancel_action(self, response: requests.Response) -> None:
        """Cancel an ongoing action."""
        invocation_data = response.json()
        response = self.client.delete(_invocation_href(invocation_data))
        response.raise_for_status()


def _get_link(obj: dict[str, Any], rel: str) -> dict[str, Any]:
    """Retrieve a link from an object's `links` list, by its `rel` attribute."""
    return next(link for link in obj["links"] if link["rel"] == rel)


def _invocation_href(invocation_data: dict[str, Any]) -> str:
    """Get the invocation href from the invocation response data."""
    return _get_link(invocation_data, "self")["href"]
