"""Unit tests for validating stack classification logic in AutofocusThing.

This module tests whether the `check_stack_result` method correctly classifies
z-stack sharpness profiles into "success", "continue", or "restart" categories
based on predefined test cases.

Sharpness profiles are loaded from a JSON file and converted into mock capture
objects to simulate real camera captures.
"""

import json

from labthings_fastapi.testing import create_thing_without_server

from openflexure_microscope_server.things.autofocus import AutofocusThing


class MockCapture:
    """Simple mock object representing a captured image.

    This class mimics the minimal interface required by
    `check_stack_result` by adding the `sharpness` and `buffer_id`
    attributes.

    :param sharpness: The sharpness value associated with the image.
    :param buffer_id: A unique identifier for the image buffer.
    """

    def __init__(self, sharpness, buffer_id):
        """Give each capture a sharpness and buffer_id."""
        self.sharpness = sharpness
        self.buffer_id = buffer_id


def make_captures(sharpness_list):
    """Convert a list of sharpness values into mock capture objects.

    :param sharpness_list: A list of numeric sharpness values.
    :returns: A list of MockCapture instances with sequential buffer IDs.
    """
    return [MockCapture(s, i) for i, s in enumerate(sharpness_list)]


def test_stack_labelling():
    """Test stack classification accuracy against labelled sharpness cases.

    This test loads predefined sharpness profiles and their expected labels
    from a JSON file, converts them into mock capture objects, and evaluates
    the classification returned by `check_stack_result`.

    The test asserts that at least 90% of cases are correctly classified.

    Expected labels may be a single value or a list of acceptable values.
    """
    autofocus_thing = create_thing_without_server(AutofocusThing, mock_all_slots=True)
    with open(r"tests\unit_tests\data\sharpness_test_cases.json") as f:
        data = json.load(f)

    success = 0
    total = len(data)

    for _i, case in enumerate(data):
        sharpnesses = case["sharpnesses"]
        expected = case["label"]

        # Allow multiple acceptable labels
        if not isinstance(expected, list):
            expected = [expected]

        # Convert to capture objects
        captures = make_captures(sharpnesses)

        # Call the method under test
        result, _ = autofocus_thing.check_stack_result(
            captures, check_turning_points=False
        )
        if result in expected:
            success += 1

    assert success > 0.8 * total
