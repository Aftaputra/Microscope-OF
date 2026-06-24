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

    name: str

    # Ensure it is a Thing:
    _thing_server_interface: lt.ThingServerInterface

    # Ensure it is an OFMThing:
    show_data_in_gallery: bool

    gallery_data_schema: type[BaseModel]

    # Ignore D102: No docstrings for the protocol.
    def get_data_for_gallery(self) -> list[BaseModel]: ...  # noqa: D102

    def delete_all_gallery_items(self) -> None: ...  # noqa: D102


class GalleryThing(lt.Thing):
    """A Thing for communicating with the front end gallery."""

    all_ofm_things: Mapping[str, OFMThing] = lt.thing_slot()

    _gallery_providing_things: Optional[Mapping[str, GalleryCompatibleThing]] = None
    _card_types: Optional[list[str]] = None
    _card_type_map: dict[str, str] = {}

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
        self._set_card_types()
        return self

    def _set_gallery_providers(self) -> None:
        """Set the mapping of gallery providing things.

        This is called on ``__enter__`` when the server starts.
        """
        gallery_providers = {
            name: thing
            for name, thing in self.all_ofm_things.items()
            if thing.show_data_in_gallery
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

    def _set_card_types(self) -> None:
        """Find the card types from each provider."""
        card_types: list[str] = []
        for thing in self.gallery_providing_things.values():
            card_schema = thing.gallery_data_schema.schema()
            props = card_schema["properties"]
            if "card_type" not in props or "const" not in props["card_type"]:
                raise TypeError(
                    f"Gallery data card for {thing.name} doesn't have a staticcard_type"
                )
            card_type = props["card_type"]["const"]
            if card_type not in card_types:
                card_types.append(card_type)
            self._card_type_map[thing.name] = card_type

        self._card_types = card_types

    @lt.property
    def card_types(self) -> list[str]:
        """Names for the card types in the gallery."""
        if self._card_types is None:
            raise RuntimeError("Cannot access card_types before server has started.")
        return self._card_types

    @lt.property
    def list_data(self) -> list[dict[str, Any]]:
        """List the data from all registered things.

        Currently only works with `smart_scan` as the UI cards are not customisable.

        This will change to an action (or another type of endpoint) at a
        later date to enable filtering, and returning only a specific page.
        """
        data_list = []
        for thing in self.gallery_providing_things.values():
            try:
                data_list += [
                    model.model_dump() for model in thing.get_data_for_gallery()
                ]
            except Exception as e:
                # If any of the providers errors producing a list, log the exception
                # and continue.
                self.logger.exception(e)
        return data_list

    @lt.action
    def delete_all_data(self, card_types: list[str]) -> None:
        """Delete all the gallery data on this microscope with the given card types."""
        for thing in self.gallery_providing_things.values():
            thing_card_type = self._card_type_map.get(thing.name)
            if thing_card_type in card_types:
                try:
                    thing.delete_all_gallery_items()
                except Exception as e:
                    self.logger.exception(e)
