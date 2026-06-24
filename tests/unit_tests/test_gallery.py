"""Tests that captures have the expected metadata."""

import logging
from dataclasses import dataclass
from typing import Callable, Optional

import pytest
from pydantic import BaseModel

from labthings_fastapi.exceptions import InvocationCancelledError
from labthings_fastapi.testing import create_thing_without_server

from openflexure_microscope_server.things import OFMThing
from openflexure_microscope_server.things.gallery import (
    GalleryCompatibleThing,
    GalleryThing,
)

from ..shared_utils.lt_test_utils import LabThingsTestEnv


def test_error_if_accessing_gallery_things_before_started():
    """Check that gallery_providing_things property errors before init."""
    thing = create_thing_without_server(GalleryThing)
    with pytest.raises(
        RuntimeError,
        match="Cannot access gallery_providing_things before server has started.",
    ):
        thing.gallery_providing_things


class MockGalleryData(BaseModel):
    """Mock gallery data."""

    mock: str
    foobar: int


class MinimalGalleryClass:
    """A class that provides data to the gallery but is NOT a thing.

    This should fail the protocol check as it is not an OFMThing
    """

    gallery_data_name: str = "Mock"

    gallery_data_schema: type[BaseModel] = MockGalleryData

    def get_data_for_gallery(self) -> list[BaseModel]:
        """Return a list of Mock Gallery Data."""
        return [MockGalleryData(mock="mock", foobar="foobar")]

    def delete_all_gallery_items(self) -> None:
        """Mock deleting all the data."""


class MinimalGallerySource(OFMThing, MinimalGalleryClass):
    """Minimal example of a Thing that can show data in the gallery.

    Mixes MinimalGalleryClass into OFMThing to be recognised by the protocol.
    """

    show_data_in_gallery = True


class BadGallerySource(OFMThing):
    """An OFMThing that almost defines enough to show in the gallery.

    Shouldn't match the protocol as ``gallery_data_name`` is missing.
    """

    show_data_in_gallery = True

    gallery_data_schema: type[BaseModel] = MockGalleryData

    def get_data_for_gallery(self) -> list[BaseModel]:
        """Return a list of Mock Gallery Data."""
        return [MockGalleryData(mock="mock", foobar="foobar")]

    def delete_all_gallery_items(self) -> None:
        """Mock deleting all the data."""


def test_gallery_compatible_protocol():
    """Check the gallery compatible protocol detects compatible classes only."""
    # Minimal class has the gallery specific methods but is not an OFMThing.
    assert not isinstance(MinimalGalleryClass(), GalleryCompatibleThing)

    # BadGallerySource is an OFM Thing but is missing one of the required properties.
    assert not isinstance(
        create_thing_without_server(BadGallerySource), GalleryCompatibleThing
    )

    # MinimalGallerySource should match!
    assert isinstance(
        create_thing_without_server(MinimalGallerySource), GalleryCompatibleThing
    )


def test_gallery_thing_finds_all_providers(simulation_test_env):
    """Check the gallery identifies the correct Things that will provide data."""
    gallery = simulation_test_env.get_thing_by_name("gallery")
    snake_workflow = simulation_test_env.get_thing_by_name("snake_workflow")
    smart_scan = simulation_test_env.get_thing_by_name("smart_scan")
    camera = simulation_test_env.get_thing_by_name("camera")

    assert snake_workflow not in gallery.all_ofm_things.values()
    assert camera in gallery.all_ofm_things.values()
    assert smart_scan in gallery.all_ofm_things.values()

    assert snake_workflow not in gallery.gallery_providing_things.values()
    assert camera in gallery.gallery_providing_things.values()
    assert smart_scan in gallery.gallery_providing_things.values()

    assert not isinstance(snake_workflow, GalleryCompatibleThing)
    assert isinstance(smart_scan, GalleryCompatibleThing)


def test_gallery_logs_for_bad_providers(caplog):
    """Test that an error is logged if a gallery source doesn't match the protocol."""
    # Create a config with the minimal Thing and the bad Thing
    things = {
        "minimal_thing": MinimalGallerySource,
        "bad_thing": BadGallerySource,
        "gallery": GalleryThing,
    }
    with caplog.at_level(logging.INFO):
        # Start the server
        with LabThingsTestEnv(
            things=things, application_config={"data_folder": "./openflexure/data/"}
        ) as env:
            gallery = env.get_thing_by_name("gallery")
            # Minimal thing is listed as a gallery provider
            assert "minimal_thing" in gallery.gallery_providing_things
            # Bad thing isn't as the protocol doesn't match
            assert "bad_thing" not in gallery.gallery_providing_things

        # There is an error logged about bad_thing
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert "Data from bad_thing cannot be shown in gallery" in record.message
        assert record.levelname == "ERROR"


@pytest.fixture
def minimal_gallery_env():
    """Return a minimal working environment for testing the gallery."""
    things = {
        "minimal_thing1": MinimalGallerySource,
        "minimal_thing2": MinimalGallerySource,
        "gallery": GalleryThing,
    }
    with LabThingsTestEnv(
        things=things, application_config={"data_folder": "./openflexure/data/"}
    ) as env:
        return env


def test_gallery_lists_data(minimal_gallery_env, mocker, caplog):
    """Test that the gallery calls all gallery things to list data."""
    # Create a config with the minimal Thing and the bad Thing
    gallery = minimal_gallery_env.get_thing_by_name("gallery")
    thing_1 = minimal_gallery_env.get_thing_by_name("minimal_thing1")
    thing_2 = minimal_gallery_env.get_thing_by_name("minimal_thing2")

    thing_1_data = [
        MockGalleryData(mock="thing_1", foobar=1),
        MockGalleryData(mock="thing_1", foobar=2),
    ]

    thing_2_data = [
        MockGalleryData(mock="thing_2", foobar=1),
        MockGalleryData(mock="thing_2", foobar=2),
    ]

    mocker.patch.object(thing_1, "get_data_for_gallery", return_value=thing_1_data)
    mocker.patch.object(thing_2, "get_data_for_gallery", return_value=thing_2_data)

    thing_1_return = [
        {"mock": "thing_1", "foobar": 1},
        {"mock": "thing_1", "foobar": 2},
    ]
    thing_2_return = [
        {"mock": "thing_2", "foobar": 1},
        {"mock": "thing_2", "foobar": 2},
    ]

    assert gallery.list_data == thing_1_return + thing_2_return

    thing_1.get_data_for_gallery.side_effect = RuntimeError
    with caplog.at_level(logging.INFO):
        assert gallery.list_data == thing_2_return
    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "ERROR"


@dataclass
class GalleryDeleteTestCase:
    """Inputs and expected outputs for testing ``save_from_memory``.

    The default save kwargs assume a jpeg.
    """

    thing_1_side_effect: Optional[Callable]
    thing_2_call_count: int
    # Expect directly calling the action will raise the thing 1 side_effect error
    action_errors: bool


GALLERY_DELETE_TEST_CASES = [
    # No errors from thing 1, thing 2 gets called
    GalleryDeleteTestCase(
        thing_1_side_effect=None, thing_2_call_count=1, action_errors=False
    ),
    # Thing 1 errors, thing 2 is still called
    GalleryDeleteTestCase(
        thing_1_side_effect=RuntimeError, thing_2_call_count=1, action_errors=False
    ),
    # Thing 1 raises invocation cancelled error. Thing 2 is not called. The InvocationError is raised
    GalleryDeleteTestCase(
        thing_1_side_effect=InvocationCancelledError,
        thing_2_call_count=0,
        action_errors=True,
    ),
]


@pytest.mark.parametrize("test_case", GALLERY_DELETE_TEST_CASES)
def test_gallery_calls_delete(test_case, minimal_gallery_env, mocker):
    """Test that the gallery deletes on all gallery providing things."""
    # Create a config with the minimal Thing and the bad Thing
    gallery = minimal_gallery_env.get_thing_by_name("gallery")
    thing_1 = minimal_gallery_env.get_thing_by_name("minimal_thing1")
    thing_2 = minimal_gallery_env.get_thing_by_name("minimal_thing2")

    mocker.patch.object(
        thing_1, "delete_all_gallery_items", side_effect=test_case.thing_1_side_effect
    )
    mocker.patch.object(thing_2, "delete_all_gallery_items")

    if test_case.action_errors:
        with pytest.raises(test_case.thing_1_side_effect):
            gallery.delete_all_data()
    else:
        gallery.delete_all_data()

    assert thing_1.delete_all_gallery_items.call_count == 1
    assert thing_2.delete_all_gallery_items.call_count == test_case.thing_2_call_count
