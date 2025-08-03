"""Testing submodule with mock Camera Things.

These mocks are designed to be inserted as dependencies to provide specific
functionality and return values.

The mocks do not subclass Things. Instead, they return predefined
answers to functions.
"""

from openflexure_microscope_server.background_detect import (
    BackgroundDetectorStatus,
    ColourChannelDetectSettings,
)
from unittest.mock import Mock, PropertyMock


class MockCameraThing(Mock):
    """A mock camera Thing that imports no code from ``BaseCamera``.

    The class needs functionality added to it over time as more complex
    mocking is needed. It imports no code from ``BaseCamera`` or any other
    camera Thing, so that coverage is not artificially inflated.
    """

    def __init__(self, *args, **kwargs):
        """Initialise the mock camera, args and kwargs are the mock args and kwargs."""
        super().__init__(*args, **kwargs)

        self.background_detector_status = PropertyMock(
            return_value=BackgroundDetectorStatus(
                ready=True,
                settings=ColourChannelDetectSettings().model_dump(),
                settings_schema={"fake": "schema"},
            )
        )
