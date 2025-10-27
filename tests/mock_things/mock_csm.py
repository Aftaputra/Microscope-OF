"""Testing submodule with mock Camera Stage Mapping Things.

These mocks are designed to be inserted as dependencies to provide specific
functionality and return values.

The mocks do not subclass Things. Instead, they return predefined
answers to functions.
"""


class MockCSMThing:
    """A mock CSM Thing that imports no code from CameraStageMapper.

    The class needs functionality added to it over time as more complex
    mocking is needed. It imports no code from CameraStageMapper so that coverage
    is not artificially inflated.
    """

    image_resolution = (123, 456)
    image_to_stage_displacement_matrix = [
        [0.03061156624485296, 1.8031242270940833],
        [1.773236372778601, 0.006660431608601435],
    ]
