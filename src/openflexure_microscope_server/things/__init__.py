"""A package for all of the core LabThings-FastAPI Things shipped with the microscope.

The microscope can be extended to be used with other hardware by creating a package
with other Things and including them in the LabThings-FastAPI config file.
"""

import os
from typing import Optional, Self

import labthings_fastapi as lt

# To ensure consistency, we enable the feature flags we want here. This means
# they will be enabled in any code that imports a `Thing` from this package.
lt.FEATURE_FLAGS.validate_properties_on_set = True


class OFMThing(lt.Thing):
    """A custom LabThings Thing class for the OpenFlexure Microscope."""

    _data_dir: Optional[str] = None

    _show_data_in_gallery: bool = False

    @property
    def show_data_in_gallery(self) -> bool:
        """Whether to show in the Gallery."""
        return self._show_data_in_gallery

    def __enter__(self) -> Self:
        """Set the data directory when the Thing is entered."""
        # Note that the `application_config` was already validated when the
        # server initialised.
        application_config = self._thing_server_interface.application_config
        if application_config is None:
            raise ValueError("No application configuration was supplied.")
        app_data_dir = application_config["data_folder"]
        self._data_dir = os.path.join(
            os.path.normpath(str(app_data_dir)), os.path.normpath(self.name)
        )
        return self

    @property
    def data_dir(self) -> str:
        """The data directory for this thing."""
        if self._data_dir is None:
            raise RuntimeError(
                "No data directory set. Has the LabThings server been started?"
            )
        return self._data_dir
