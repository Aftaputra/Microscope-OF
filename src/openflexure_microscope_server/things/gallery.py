"""Server-side gallery functionality.

The types of data that are captured and how they display in the gallery are defined by
the Things that capture the Data. This thing just provides a unified way for the gallery
front end to access the data.
"""

from typing import Any, Mapping, Optional, Protocol, Self, cast, runtime_checkable

from pydantic import BaseModel

import labthings_fastapi as lt

from openflexure_microscope_server.things import OFMThing


@runtime_checkable
class GalleryCompatibleThing(Protocol):
    """Protocol for checking Things using the gallery are complete.

    Note that runtime checkable protocols only check that the methods exist, not the
    full signatures. This means that anything attempting to define the methods will
    be picked up, but may throw an error when used.
    """

    # Ensure it is a Thing:
    _thing_server_interface: lt.ThingServerInterface

    # Ensure it is an OFMThing:
    show_in_gallery: bool

    gallery_data_name: str

    gallery_data_schema: type[BaseModel]

    # Ignore D102: No docstrings for the protocol.
    def get_gallery_data(self) -> list[BaseModel]: ...  # noqa: D102


class GalleryThing(lt.Thing):
    """A Thing for communicating with the front end gallery."""

    all_ofm_things: Mapping[str, OFMThing] = lt.thing_slot()

    _gallery_providing_things: Optional[Mapping[str, GalleryCompatibleThing]] = None

    @property
    def gallery_providing_things(self) -> Mapping[str, GalleryCompatibleThing]:
        """All Things that provide data to the gallery."""
        if self._gallery_providing_things is None:
            raise RuntimeError(
                "Cannot access gallery_providing_things before server has started."
            )
        return self._gallery_providing_things

    def __enter__(self) -> Self:
        """Check for all gallery providing things on server startup."""
        self._set_gallery_providers()
        return self

    def _set_gallery_providers(self) -> None:
        """Set the mapping of gallery providing things.

        This is called on ``__enter__`` when the server starts.
        """
        gallery_providers = {
            name: thing
            for name, thing in self.all_ofm_things.items()
            if thing.show_in_gallery
        }
        # cache initial list of keys as it may change in the loop
        keys = list(gallery_providers.keys())
        for key in keys:
            if not isinstance(gallery_providers[key], GalleryCompatibleThing):
                self.logger.error(
                    f"Data from {key} cannot be shown in gallery as it does not "
                    "provide all necessary properties/methods for the gallery."
                )
                gallery_providers.pop(key)

        # Cast the type of each thing to "GalleryCompatibleThing" as other Things have
        # been popped.
        self._gallery_providing_things = cast(
            Mapping[str, GalleryCompatibleThing], gallery_providers
        )

    @lt.property
    def list_data(self) -> list[dict[str, Any]]:
        """List the data from all registered things.

        Currently only works with `smart_scan` as the UI cards are not customisable.

        This will change to an action (or another type of endpoint) at a
        later date to enable filtering, and returning only a specific page.
        """
        data_list = []
        for thing in self.gallery_providing_things.values():
            data_list += [model.model_dump() for model in thing.get_gallery_data()]
        return data_list
