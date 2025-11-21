"""Tests for the smart and fast stacking."""

from typing import Optional
import tempfile
from random import randint
import logging

import pytest
import numpy as np
from hypothesis import given, strategies as st
from fastapi.testclient import TestClient

import labthings_fastapi as lt

from openflexure_microscope_server.things.autofocus import (
    AutofocusThing,
    StackParams,
    CaptureInfo,
    MIN_TEST_IMAGE_COUNT,
    MAX_TEST_IMAGE_COUNT,
    _get_capture_by_id,
    _get_capture_index_by_id,
)
from openflexure_microscope_server.scan_directories import IMAGE_REGEX

LOGGER = logging.getLogger("mock-invocation_logger")
RANDOM_GENERATOR = np.random.default_rng()


def odd_integers(min_value=0, max_value=1000):
    """Return a hypothesis strategy for odd integers."""
    min_base = (min_value) // 2
    max_base = (max_value - 1) // 2
    # Ensure the range allows at least one odd number
    if min_base > max_base:
        return st.nothing()
    return st.integers(min_value=min_base, max_value=max_base).map(lambda x: 2 * x + 1)


def even_integers(min_value=0, max_value=1000):
    """Return a hypothesis strategy for even integers."""
    min_base = (min_value + 1) // 2
    max_base = (max_value) // 2
    # Ensure the range allows at least one even number
    if min_base > max_base:
        return st.nothing()
    return st.integers(min_value=min_base, max_value=max_base).map(lambda x: 2 * x)


@given(
    save_ims=odd_integers(min_value=1, max_value=9),
    extra_ims=even_integers(min_value=0, max_value=10),
)
def test_stack_params_validation(save_ims, extra_ims):
    """Test the validation of the image numbers for a stack for valid combinations.

    save_ims is the number to save (must be odd and positive)
    extra_ims is how many more images there are in min_images_to_test than
    images_to_save. (even so that, min_images_to_test is odd and larger than
    images_to_save
    """
    # Coerce min_images_to_test as the max extra ims depends on save_ims so is hard
    # to do automatically in hypothesis. This clamps the number between 3 and 9.
    min_images_to_test = max(min(save_ims + extra_ims, 9), 3)
    StackParams(
        stack_dz=50,
        images_to_save=save_ims,
        min_images_to_test=min_images_to_test,
        autofocus_dz=2000,
        images_dir="/this/is/fake",
        save_resolution=(1640, 1232),
    )


@given(
    save_ims=odd_integers(min_value=0, max_value=10),
    extra_ims=even_integers(min_value=-10, max_value=-1),
)
def test_stack_params_not_enough_test_images(save_ims, extra_ims):
    """Test error is raised if min_images_to_test is smaller than images_to_save.

    ``extra_ims`` negative so that min_images_to_test is smaller than images_to_save.

    For arguments see test_stack_params_validation
    """
    # Depending on the values multiple messages are possible
    match = (
        "(Can't test for focus with fewer than 3 images|"
        "Can't save more images than the minimum number tested)"
    )
    with pytest.raises(ValueError, match=match):
        StackParams(
            stack_dz=50,
            images_to_save=save_ims,
            min_images_to_test=save_ims + extra_ims,
            autofocus_dz=2000,
            images_dir="/this/is/fake",
            save_resolution=(1640, 1232),
        )


@given(
    save_ims=odd_integers(min_value=-10, max_value=-1),
    extra_ims=even_integers(min_value=0, max_value=10),
)
def test_stack_params_negative_images_to_save(save_ims, extra_ims):
    """save_ims is negative so images_to_save is negative, failing validation.

    For arguments see test_stack_params_validation
    """
    # Depending on the values multiple messages are possible
    match = (
        "(Can't test for focus with fewer than 3 images|"
        "Images to save must be positive and odd)"
    )
    with pytest.raises(ValueError, match=match):
        StackParams(
            stack_dz=50,
            images_to_save=save_ims,
            min_images_to_test=save_ims + extra_ims,
            autofocus_dz=2000,
            images_dir="/this/is/fake",
            save_resolution=(1640, 1232),
        )


@given(
    save_ims=odd_integers(min_value=0, max_value=10),
    extra_ims=odd_integers(min_value=0, max_value=10),
)
def test_even_min_images_to_test(save_ims, extra_ims):
    """extra_ims is odd so min_images_to_test is even, failing validation.

    For arguments see test_stack_params_validation
    """
    # Depending on the values multiple messages are possible
    match = (
        "(Can't test for focus with fewer than 3 images|"
        "Testing with more than 9 images is|"  # may give more than 9 which errors first
        "Minimum number of images to test should be positive and odd)"
    )
    with pytest.raises(ValueError, match=match):
        StackParams(
            stack_dz=50,
            images_to_save=save_ims,
            min_images_to_test=save_ims + extra_ims,
            autofocus_dz=2000,
            images_dir="/this/is/fake",
            save_resolution=(1640, 1232),
        )


@given(
    save_ims=even_integers(min_value=0, max_value=10),
    extra_ims=odd_integers(min_value=0, max_value=10),
)
def test_even_images_to_save(save_ims, extra_ims):
    """save_ims is even so images_to_save is even, failing validation.

    For arguments see test_stack_params_validation
    """
    match = (
        "(Can't test for focus with fewer than 3 images|"
        "Images to save must be positive and odd)"
    )
    with pytest.raises(ValueError, match=match):
        StackParams(
            stack_dz=50,
            images_to_save=save_ims,
            min_images_to_test=save_ims + extra_ims,
            autofocus_dz=2000,
            images_dir="/this/is/fake",
            save_resolution=(1640, 1232),
        )


def test_computed_stack_params():
    """Test StackParams computed properties are as expected.

    Not using hypothesis or we will just copy in the same formulas.
    """
    stack_parameters = StackParams(
        stack_dz=50,
        images_to_save=5,
        min_images_to_test=9,
        autofocus_dz=2000,
        images_dir="/this/is/fake",
        save_resolution=(1640, 1232),
    )

    assert stack_parameters.stack_z_range == 8 * 50

    assert stack_parameters.steps_undershoot == stack_parameters.img_undershoot * 50

    assert stack_parameters.max_images_to_test == 9 + 15

    sharpnesses = [50, 77, 234, 324, 390, 496, 569, 454, 333, 222, 178, 70]
    max_ind = np.argmax(sharpnesses)
    slice_to_save = stack_parameters.slice_to_save(max_ind)
    # Check the slice corresponds to the index for the 5 images centred on the sharpest
    assert sharpnesses[slice_to_save] == [390, 496, 569, 454, 333]

    # For a failed smart stack the slice may be truncated. Check it truncates correctly
    sharpnesses = [496, 569, 454, 333, 222, 178, 70, 69, 66, 50, 45, 40]
    max_ind = np.argmax(sharpnesses)
    slice_to_save = stack_parameters.slice_to_save(max_ind)
    # Check the slice corresponds to the index for the first 4 images
    assert sharpnesses[slice_to_save] == [496, 569, 454, 333]

    # And again for sharpest at the end
    sharpnesses = [13, 21, 26, 31, 39, 49, 50, 77, 234, 324, 390, 496, 569]
    max_ind = np.argmax(sharpnesses)
    slice_to_save = stack_parameters.slice_to_save(max_ind)
    # Check the slice corresponds to the index for the final 3 images
    assert sharpnesses[slice_to_save] == [390, 496, 569]


def random_capture(set_id: Optional[int] = None):
    """Create a capture with random values.

    :param set_id: Optional, use to set a fixed id rather than a random one
    """
    buffer_id = set_id if set_id is not None else randint(0, 1000)
    return CaptureInfo(
        buffer_id=buffer_id,
        position={
            "x": randint(-100000, 100000),
            "y": randint(-100000, 100000),
            "z": randint(-100000, 100000),
        },
        sharpness=randint(0, 100000),
    )


def test_capture_filename_matches_regex():
    """For 100 random captures check the image always matches the regex."""
    for _ in range(100):
        assert IMAGE_REGEX.search(random_capture().filename)


@given(st.integers(min_value=0, max_value=5000))
def test_retrieval_of_captures(start):
    """For 20 random captures, check each can be retrieved correctly by id."""
    captures = [random_capture(start + i) for i in range(20)]

    for i, capture in enumerate(captures):
        buffer_id = capture.buffer_id
        assert _get_capture_index_by_id(captures, buffer_id) == i
        assert _get_capture_by_id(captures, buffer_id) is capture

    # Check errors are raised when supplying ids that aren't in the list
    with pytest.raises(ValueError, match="No capture has a buffer id of"):
        _get_capture_index_by_id(captures, start - 1)
    with pytest.raises(ValueError, match="No capture has a buffer id of"):
        _get_capture_index_by_id(captures, start + 21)
    with pytest.raises(ValueError, match="No capture has a buffer id of"):
        _get_capture_by_id(captures, start - 1)
    with pytest.raises(ValueError, match="No capture has a buffer id of"):
        _get_capture_by_id(captures, start + 21)


@pytest.fixture
def autofocus_thing():
    """Yield an autofocus thing connected to a server."""
    autofocus_thing = AutofocusThing()
    with tempfile.TemporaryDirectory() as tmpdir:
        server = lt.ThingServer(settings_folder=tmpdir)
        server.add_thing(autofocus_thing, "/autofocus/")
        with TestClient(server.app):
            yield autofocus_thing


def test_create_stack(autofocus_thing, caplog):
    """Run create stack with default values and check there is no coercion or logging."""
    initial_min_images_to_test = autofocus_thing.stack_min_images_to_test
    initial_images_to_save = autofocus_thing.stack_images_to_save
    with caplog.at_level(logging.INFO):
        stack_params = autofocus_thing.create_stack_params(
            autofocus_dz=2000,
            images_dir="/this/is/fake",
            save_resolution=(1640, 1232),
            logger=LOGGER,
        )

    assert len(caplog.records) == 0
    assert autofocus_thing.stack_min_images_to_test == initial_min_images_to_test
    assert autofocus_thing.stack_images_to_save == initial_images_to_save
    assert stack_params.min_images_to_test == autofocus_thing.stack_min_images_to_test
    assert stack_params.images_to_save == autofocus_thing.stack_images_to_save


@pytest.mark.parametrize(
    ("initial_test_ims", "coerced_test_ims", "expected_log_start"),
    [
        (0, MIN_TEST_IMAGE_COUNT, "Cannot test only 0"),
        (-1, MIN_TEST_IMAGE_COUNT, "Cannot test only -1"),
        (10, MAX_TEST_IMAGE_COUNT, "Testing 10 images will"),
        (4, 5, "Minimum number of images to test should be odd"),
    ],
)
def test_coercing_stack_test_ims(
    initial_test_ims, coerced_test_ims, expected_log_start, autofocus_thing, caplog
):
    """Run create stack with images to test set to values requiring coercion, and check result."""
    autofocus_thing.stack_min_images_to_test = initial_test_ims

    with caplog.at_level(logging.WARNING):
        stack_params = autofocus_thing.create_stack_params(
            autofocus_dz=2000,
            images_dir="/this/is/fake",
            save_resolution=(1640, 1232),
            logger=LOGGER,
        )

    assert len(caplog.records) == 1
    assert str(caplog.records[0].msg).startswith(expected_log_start)
    # Check the value is coerced in the stack_params
    assert stack_params.min_images_to_test == coerced_test_ims
    # Check that the setting in the Thing was updated to the coerced value
    assert stack_params.min_images_to_test == autofocus_thing.stack_min_images_to_test


@pytest.mark.parametrize(
    ("initial_save_ims", "coerced_save_ims", "expected_log_start"),
    [
        (0, 1, "At least 1 images must be saved"),
        (-1, 1, "At least 1 images must be saved"),
        (10, 9, "Cannot save 10 images"),
        (4, 5, "Images to save should be odd, setting to 5"),
    ],
)
def test_coercing_stack_save_ims(
    initial_save_ims, coerced_save_ims, expected_log_start, autofocus_thing, caplog
):
    """Run create stack with images to save set to values requiring coercion, and check result."""
    autofocus_thing.stack_images_to_save = initial_save_ims

    with caplog.at_level(logging.WARNING):
        stack_params = autofocus_thing.create_stack_params(
            autofocus_dz=2000,
            images_dir="/this/is/fake",
            save_resolution=(1640, 1232),
            logger=LOGGER,
        )

    assert len(caplog.records) == 1
    assert str(caplog.records[0].msg).startswith(expected_log_start)
    # Check the value is coerced in the stack_params
    assert stack_params.images_to_save == coerced_save_ims
    # Check that the setting in the Thing was updated to the coerced value
    assert stack_params.images_to_save == autofocus_thing.stack_images_to_save


@pytest.mark.parametrize("pass_on", [1, 2, 3, 4])
def test_run_smart_stack(pass_on, autofocus_thing, mocker):
    """Test Running smart stack with the stack passing on different attempts."""
    cam = mocker.Mock()
    stage = mocker.Mock()
    sharpness_monitor = mocker.MagicMock()
    stack_params = autofocus_thing.create_stack_params(
        autofocus_dz=2000,
        images_dir="/this/is/fake",
        save_resolution=(1640, 1232),
        logger=LOGGER,
    )
    assert stack_params.max_attempts == 3

    # Set up returns from z-stack
    fake_captures = [
        CaptureInfo(
            buffer_id="first", position={"x": 0, "y": 0, "z": -99}, sharpness=123
        ),
        CaptureInfo(
            buffer_id="pick_me", position={"x": 0, "y": 0, "z": 555}, sharpness=456
        ),
        CaptureInfo(
            buffer_id="last", position={"x": 0, "y": 0, "z": 999}, sharpness=123
        ),
    ]

    successful_return = (True, fake_captures, "pick_me")
    failed_return = (False, fake_captures, "pick_me")
    return_list = [failed_return] * (pass_on - 1) + [successful_return]

    # Mock z_stack and looping_autofocus
    autofocus_thing.z_stack = mocker.Mock(side_effect=return_list)
    autofocus_thing.looping_autofocus = mocker.Mock()

    # Run it
    success, final_z = autofocus_thing.run_smart_stack(
        cam=cam,
        stage=stage,
        sharpness_monitor=sharpness_monitor,
        stack_parameters=stack_params,
        save_on_failure=False,
        check_turning_points=True,
    )

    # Only passes if the attempt it passes on is less than max attempts
    assert success == (pass_on <= stack_params.max_attempts)
    # Final z is the one from the id returned by the stack "pick_me"
    assert final_z == 555

    # z_stack should run up until the time it passes. Running no more than max_attempts
    n_stacks = min(pass_on, stack_params.max_attempts)
    assert autofocus_thing.z_stack.call_count == n_stacks
    # Move absolute should be 1 less time that the number of times z_stack_run
    assert stage.move_absolute.call_count == n_stacks - 1
    # As should looping autofocus
    assert autofocus_thing.looping_autofocus.call_count == n_stacks - 1

    # Check rest stack is moving to the first image in the stack.
    if n_stacks > 1:
        assert stage.move_absolute.call_args.kwargs["z"] == -99

    # Mock called to save image
    assert cam.save_from_memory.call_count == (1 if success else 0)
