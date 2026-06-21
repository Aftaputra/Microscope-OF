"""Tests that captures have the expected metadata."""

import logging

from pydantic import BaseModel

from labthings_fastapi.testing import create_thing_without_server

from openflexure_microscope_server.things import OFMThing
from openflexure_microscope_server.things.gallery import (
    GalleryCompatibleThing,
    GalleryThing,
)

from ..shared_utils.lt_test_utils import LabThingsTestEnv


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
