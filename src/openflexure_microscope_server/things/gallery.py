"""Server-side gallery functionality.

The types of data that are captured and how they display in the gallery are defined by
the Things that capture the Data. This thing just provides a unified way for the gallery
front end to access the data.
"""

from typing import Mapping, Optional

import labthings_fastapi as lt

from openflexure_microscope_server.things import OFMThing


class GalleryThing(lt.Thing):
    """A Thing for communicating with the front end gallery."""

    all_ofm_things: Mapping[str, OFMThing] = lt.thing_slot()

    _gallery_providing_things: Optional[Mapping[str, OFMThing]] = None

    @property
    def gallery_providing_things(self) -> Mapping[str, OFMThing]:
        """All Things that provide data to the gallery."""
        if self._gallery_providing_things is None:
            self._gallery_providing_things = {
                name: thing
                for name, thing in self.all_ofm_things.items()
                if thing.show_in_gallery
            }
        return self._gallery_providing_things
