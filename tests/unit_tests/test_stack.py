"""Tests for the smart and fast stacking."""

import logging
from random import randint
from typing import Optional

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from labthings_fastapi.testing import create_thing_without_server

from openflexure_microscope_server.scan_directories import IMAGE_REGEX
from openflexure_microscope_server.things.autofocus import (
    EXTRA_STACK_CAPTURES,
    MAX_TEST_IMAGE_COUNT,
    MIN_TEST_IMAGE_COUNT,
    AutofocusThing,
    CaptureInfo,
    NotAPeakError,
    SmartStackParams,
    StackOrigin,
    StackParams,
    _count_turning_points,
    _get_capture_by_id,
    _get_capture_index_by_id,
    _get_peak_turning_point,
)
from openflexure_microscope_server.things.scan_workflows import HistoScanWorkflow

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
    SmartStackParams(
        stack_dz=50, images_to_save=save_ims, min_images_to_test=min_images_to_test
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
        SmartStackParams(
            stack_dz=50,
            images_to_save=save_ims,
            min_images_to_test=save_ims + extra_ims,
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
        SmartStackParams(
            stack_dz=50,
            images_to_save=save_ims,
            min_images_to_test=save_ims + extra_ims,
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
        SmartStackParams(
            stack_dz=50,
            images_to_save=save_ims,
            min_images_to_test=save_ims + extra_ims,
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
        SmartStackParams(
            stack_dz=50,
            images_to_save=save_ims,
            min_images_to_test=save_ims + extra_ims,
        )


def test_computed_stack_params():
    """Test SmartStackParams computed properties are as expected.

    Not using hypothesis or we will just copy in the same formulas.
    """
    stack_parameters = SmartStackParams(
        stack_dz=50, images_to_save=5, min_images_to_test=9
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
    """Return an autofocus thing connected to a server."""
    return create_thing_without_server(AutofocusThing, mock_all_slots=True)


@pytest.fixture
def histo_scan_workflow():
    """Return an autofocus thing connected to a server."""
    workflow = create_thing_without_server(
        HistoScanWorkflow,
        mock_all_slots=True,
    )

    # Minimal CSM setup so all_settings() works
    workflow._csm.image_resolution = (1000, 1000)
    workflow._csm.calibration_required = False
    workflow._csm.convert_image_to_stage_coordinates = lambda x, y: {"x": x, "y": y}

    return workflow


def test_create_stack(histo_scan_workflow, caplog):
    """Run create stack with default values and check there is no coercion or logging."""
    initial_min_images_to_test = histo_scan_workflow.stack_min_images_to_test
    initial_images_to_save = histo_scan_workflow.stack_images_to_save
    with caplog.at_level(logging.INFO):
        stack_params = histo_scan_workflow.create_smart_stack_params()

    assert len(caplog.records) == 0
    assert histo_scan_workflow.stack_min_images_to_test == initial_min_images_to_test
    assert histo_scan_workflow.stack_images_to_save == initial_images_to_save
    assert (
        stack_params.min_images_to_test == histo_scan_workflow.stack_min_images_to_test
    )
    assert stack_params.images_to_save == histo_scan_workflow.stack_images_to_save


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
    initial_test_ims, coerced_test_ims, expected_log_start, histo_scan_workflow, caplog
):
    """Run create stack with images to test set to values requiring coercion, and check result."""
    histo_scan_workflow.stack_min_images_to_test = initial_test_ims

    with caplog.at_level(logging.WARNING):
        stack_params = histo_scan_workflow.create_smart_stack_params()

    assert len(caplog.records) == 1
    assert str(caplog.records[0].msg).startswith(expected_log_start)
    # Check the value is coerced in the stack_params
    assert stack_params.min_images_to_test == coerced_test_ims
    # Check that the setting in the Thing was updated to the coerced value
    assert (
        stack_params.min_images_to_test == histo_scan_workflow.stack_min_images_to_test
    )


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
    initial_save_ims, coerced_save_ims, expected_log_start, histo_scan_workflow, caplog
):
    """Run create stack with images to save set to values requiring coercion, and check result."""
    histo_scan_workflow.stack_images_to_save = initial_save_ims

    with caplog.at_level(logging.WARNING):
        stack_params = histo_scan_workflow.create_smart_stack_params()

    assert len(caplog.records) == 1
    assert str(caplog.records[0].msg).startswith(expected_log_start)
    # Check the value is coerced in the stack_params
    assert stack_params.images_to_save == coerced_save_ims
    # Check that the setting in the Thing was updated to the coerced value
    assert stack_params.images_to_save == histo_scan_workflow.stack_images_to_save


@pytest.mark.parametrize("pass_on", [1, 2, 3, 4])
def test_run_smart_stack(pass_on, histo_scan_workflow, autofocus_thing, mocker):
    """Test Running smart stack with the stack passing on different attempts."""
    scan_settings, _ = histo_scan_workflow.all_settings(images_dir="dummy")
    assert scan_settings.smart_stack_params.max_attempts == 3

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

    # Mock smart_z_stack and looping_autofocus
    autofocus_thing.smart_z_stack = mocker.Mock(side_effect=return_list)
    autofocus_thing.looping_autofocus = mocker.Mock()

    # Run it
    success, final_z = autofocus_thing.run_smart_stack(
        stack_parameters=scan_settings.smart_stack_params,
        capture_parameters=scan_settings.capture_params,
        autofocus_parameters=scan_settings.autofocus_params,
    )

    # Only passes if the attempt it passes on is less than max attempts
    assert success == (pass_on <= scan_settings.smart_stack_params.max_attempts)
    # Final z is the one from the id returned by the stack "pick_me"
    assert final_z == 555

    # smart_z_stack should run up until the time it passes. Running no more than
    # max_attempts
    n_stacks = min(pass_on, scan_settings.smart_stack_params.max_attempts)
    assert autofocus_thing.smart_z_stack.call_count == n_stacks
    # Move absolute should be 1 less time that the number of times z_stack_run
    assert autofocus_thing._stage.move_absolute.call_count == n_stacks - 1
    # As should looping autofocus
    assert autofocus_thing.looping_autofocus.call_count == n_stacks - 1

    # Check rest stack is moving to the first image in the stack.
    if n_stacks > 1:
        assert autofocus_thing._stage.move_absolute.call_args.kwargs["z"] == -99

    # Mock called to save image
    assert autofocus_thing._cam.save_from_memory.call_count == (1 if success else 0)


def setup_and_run_smart_z_stack(
    check_returns, check_turning_points, histo_scan_workflow, autofocus_thing, mocker
):
    """Set up a smart_z_stack, run it, and return the result.

    :param check_returns: The return values from check_stack_result. Note that if this
        is a list, it will be set as a side effect (and should be a list of tuples of
        results). If it a tuple (or anything else), it is set as a return value.
    """
    stack_params = histo_scan_workflow.create_smart_stack_params()
    stack_params.settling_time = 0  # Don't settle or tests take forever.

    autofocus_thing.capture_stack_image = mocker.Mock()
    if isinstance(check_returns, list):
        autofocus_thing.check_stack_result = mocker.Mock(side_effect=check_returns)
    else:
        autofocus_thing.check_stack_result = mocker.Mock(return_value=check_returns)
    return autofocus_thing.smart_z_stack(
        stack_parameters=stack_params,
        check_turning_points=check_turning_points,
    )


def test_z_stack_turning_toggle_passed(histo_scan_workflow, autofocus_thing, mocker):
    """Check that the toggling of turning points is passed to the check."""
    check_returns = ("success", "mock_id")
    for check_turning in [True, False]:
        setup_and_run_smart_z_stack(
            check_returns, check_turning, histo_scan_workflow, autofocus_thing, mocker
        )
        check_kwargs = autofocus_thing.check_stack_result.call_args.kwargs
        assert check_kwargs["check_turning_points"] == check_turning


def test_z_stack_returns_on_success_and_restart(
    histo_scan_workflow, autofocus_thing, mocker
):
    """Check that if the check returns success or restart then the stack exits with correct return value."""
    for result in ["success", "restart"]:
        check_returns = (result, "mock_id")
        ret = setup_and_run_smart_z_stack(
            check_returns, True, histo_scan_workflow, autofocus_thing, mocker
        )
        assert autofocus_thing.check_stack_result.call_count == 1
        # Check the number of images taken is exactly the call count.
        ims_taken = autofocus_thing.capture_stack_image.call_count
        assert ims_taken == histo_scan_workflow.stack_min_images_to_test
        # And the result is as expected.
        assert ret[0] == (result == "success")


def test_z_stack_exits_if_focus_never_found(
    histo_scan_workflow, autofocus_thing, mocker
):
    """Check that if the check returns continue the stack exits eventually with a failure."""
    check_returns = ("continue", "mock_id")
    ret = setup_and_run_smart_z_stack(
        check_returns, True, histo_scan_workflow, autofocus_thing, mocker
    )

    assert autofocus_thing.check_stack_result.call_count == EXTRA_STACK_CAPTURES + 1
    # Check the number of images taken is the maximum possible, set by the min images to
    # test and the number of extra images that can be taken
    ims_taken = autofocus_thing.capture_stack_image.call_count
    max_ims = histo_scan_workflow.stack_min_images_to_test + EXTRA_STACK_CAPTURES
    assert ims_taken == max_ims
    # And the result is as expected.
    assert not ret[0]


def test_z_stack_return(histo_scan_workflow, autofocus_thing, mocker):
    """Check z-stack returns as expected for more complex cases the fixed results above."""
    for i in range(2, EXTRA_STACK_CAPTURES):
        check_returns = [
            ("restart" if j == i - 1 else "continue", f"id_{j}") for j in range(i)
        ]
        ret = setup_and_run_smart_z_stack(
            check_returns, True, histo_scan_workflow, autofocus_thing, mocker
        )
        # Calculate images taken
        images_taken = histo_scan_workflow.stack_min_images_to_test + i - 1
        assert autofocus_thing.capture_stack_image.call_count == images_taken
        # Check it reports a failure
        assert not ret[0]

        # Repeat ending with a success rather than a failure
        check_returns = [
            ("success" if j == i - 1 else "continue", f"id_{j}") for j in range(i)
        ]
        ret = setup_and_run_smart_z_stack(
            check_returns, True, histo_scan_workflow, autofocus_thing, mocker
        )
        # Calculate images taken
        assert autofocus_thing.capture_stack_image.call_count == images_taken
        # Check it reports a success
        assert ret[0]


def test_capture_stack_image(autofocus_thing):
    """Check that capture stack image calls the expected functions and returns the expected data."""
    autofocus_thing._stage.position = {"x": 123, "y": 456, "z": 789}
    autofocus_thing._cam.capture_to_memory.return_value = "fake_buffer_id"
    autofocus_thing._cam.grab_jpeg_size.return_value = 54321
    buffer_max = 11

    info = autofocus_thing.capture_stack_image(buffer_max=buffer_max)
    assert autofocus_thing._cam.capture_to_memory.call_count == 1
    assert autofocus_thing._cam.grab_jpeg_size.call_count == 1
    assert info.buffer_id == "fake_buffer_id"
    assert info.position == {"x": 123, "y": 456, "z": 789}
    assert info.sharpness == 54321


def mock_capture(buffer_id: int, sharpness: int) -> CaptureInfo:
    """Create a CaptureInfo instance with a dummy position."""
    return CaptureInfo(
        buffer_id=buffer_id,
        position={"x": 0, "y": 0, "z": buffer_id},
        sharpness=sharpness,
    )


def test_check_stack_single_image_returns_success(autofocus_thing):
    """A single image is always successful."""
    captures = [mock_capture("mock-id", 10)]
    result, cap_id = autofocus_thing.check_stack_result(
        captures, check_turning_points=False
    )
    assert result == "success"
    assert cap_id == "mock-id"


@pytest.mark.parametrize(
    ("sharpnesses", "expected"),
    [
        ([5, 10, 3], "success"),
        ([10, 4, 2], "restart"),
        ([1, 2, 10], "continue"),
    ],
)
def test_check_stack_three_image_logic(sharpnesses, expected, autofocus_thing):
    """For 3 images, success is the highest one is central."""
    captures = [mock_capture(i, s) for i, s in enumerate(sharpnesses)]
    result, _ = autofocus_thing.check_stack_result(captures, check_turning_points=False)
    assert result == expected


def _run_check_stack_with_good_peak(autofocus_thing, count_turnings=False):
    """Run check stack on a good peak that should pass, and return the result.

    This can be used to check how other mocked results of subfunctions affects the
    result.
    """
    # Create an obvious peak that would normally pass.
    sharpnesses = [1, 2, 4, 7, 12, 7, 4, 2, 1]
    captures = [mock_capture(i, s) for i, s in enumerate(sharpnesses)]

    result, cap_id = autofocus_thing.check_stack_result(
        captures, check_turning_points=count_turnings
    )
    # Nothing a mocked function does should change which is the sharpest image.
    assert cap_id == 4
    return result


def test_check_stack_continues_if_no_tuning_point(autofocus_thing, mocker):
    """Check that continue is returned if no turning point is found."""
    # Mock to simulate not finding a peak
    mocker.patch(
        "openflexure_microscope_server.things.autofocus._get_peak_turning_point",
        side_effect=NotAPeakError,
    )
    result = _run_check_stack_with_good_peak(autofocus_thing)
    # Check that the NotAPeakError causes it to continue instead.
    assert result == "continue"


@pytest.mark.parametrize(
    ("location", "expected"),
    [
        (-10, "restart"),  # Restart if lower than 1.5 (halfway between im 2 and 3)
        (-1, "restart"),
        (0, "restart"),
        (1, "restart"),
        (1.49, "restart"),
        (1.5, "success"),  # Success up to 6.5 (as we have 9 images, final index is 8)
        (2.5, "success"),
        (4.5, "success"),
        (6.5, "success"),
        (6.51, "continue"),  # Continue if thrung point is after 6.5
        (7, "continue"),
        (8.1, "continue"),
        (123, "continue"),
    ],
)
def test_check_stack_affected_by_turning_point_location(
    location, expected, autofocus_thing, mocker
):
    """Check that the turning point location affects the return as expected."""
    # Mock to give the turning point location specified
    mocker.patch(
        "openflexure_microscope_server.things.autofocus._get_peak_turning_point",
        return_value=location,
    )
    result = _run_check_stack_with_good_peak(autofocus_thing)
    assert result == expected


def test_check_stack_affected_by_number_of_turning_points(autofocus_thing, mocker):
    """Check that the turning point location affects the return as expected."""
    # Set the turning point to the centre
    mocker.patch(
        "openflexure_microscope_server.things.autofocus._get_peak_turning_point",
        return_value=5,
    )
    mocker.patch(
        "openflexure_microscope_server.things.autofocus._count_turning_points",
        return_value=1,
    )
    result = _run_check_stack_with_good_peak(autofocus_thing, count_turnings=True)
    # Successful with 1 peak
    assert result == "success"

    # Change return to be 2 peaks
    mocker.patch(
        "openflexure_microscope_server.things.autofocus._count_turning_points",
        return_value=2,
    )
    result = _run_check_stack_with_good_peak(autofocus_thing, count_turnings=True)
    # Continue with 2 peaks
    assert result == "continue"
    # Unless this check is turned off
    result = _run_check_stack_with_good_peak(autofocus_thing, count_turnings=False)
    assert result == "success"


def test_get_peak_turning_point():
    """Check that the peak fitting returns expected value (or error)."""
    with pytest.raises(NotAPeakError):
        _get_peak_turning_point(np.ones(9))

    linear = np.arange(9)
    u_shape = 2 * (linear - 4) ** 2 + 17
    peak = -2 * (linear - 4) ** 2 + 55

    with pytest.raises(NotAPeakError):
        _get_peak_turning_point(linear)

    with pytest.raises(NotAPeakError):
        _get_peak_turning_point(u_shape)

    # Should be 4 to within a fitting error
    assert abs(_get_peak_turning_point(peak) - 4) < 1e-7


def test_count_turning_points():
    """Check the turing point count works as expected."""
    linear = np.arange(9)
    u_shape = 2 * (linear - 4) ** 2 + 17
    peak = -2 * (linear - 4) ** 2 + 55
    assert _count_turning_points(np.ones(9)) == 0
    assert _count_turning_points(linear) == 0
    assert _count_turning_points(u_shape) == 1
    assert _count_turning_points(peak) == 1

    assert _count_turning_points(np.array([1, 2, 3, 4, 5, 4, 3, 2, 1])) == 1
    # Double peak is 3 points
    assert _count_turning_points(np.array([1, 2, 3, 4, 2, 4, 3, 2, 1])) == 3
    # But only one if the dip isn't prominent
    assert _count_turning_points(np.array([1, 2, 3, 4, 3.8, 4, 3, 2, 1])) == 1


@pytest.fixture
def fake_capture(autofocus_thing):
    """Return a fake capture function using the current stage Z position."""

    def _fake_capture(*_args, **_kwargs):
        z = autofocus_thing._stage.position["z"]
        return CaptureInfo(
            buffer_id=f"id_{z}",
            position={"x": 0, "y": 0, "z": z},
            sharpness=1,
        )

    return _fake_capture


@pytest.fixture
def fake_move_relative(autofocus_thing):
    """Return a fake move_relative function updating the stage Z position."""

    def _fake_move_relative(z, **_kwargs):
        autofocus_thing._stage.position["z"] += z

    return _fake_move_relative


def test_run_basic_stack_simple(
    autofocus_thing, mocker, fake_capture, fake_move_relative
):
    """Basic stack captures correct number of images and saves them."""
    stack_params = StackParams(
        stack_dz=10,
        images_to_save=3,
        settling_time=0,
        backlash_correction=0,
        origin=StackOrigin.START,
    )

    capture_params = mocker.Mock()
    capture_params.images_dir = "dummy"
    capture_params.save_resolution = (100, 100)

    autofocus_thing._stage.position = {"x": 0, "y": 0, "z": 0}

    autofocus_thing.capture_stack_image = mocker.Mock(side_effect=fake_capture)

    autofocus_thing._stage.move_relative = mocker.Mock(side_effect=fake_move_relative)

    autofocus_thing._cam.save_from_memory = mocker.Mock()
    autofocus_thing._cam.clear_buffers = mocker.Mock()

    final_z, z_positions = autofocus_thing.run_basic_stack(
        stack_parameters=stack_params,
        capture_parameters=capture_params,
    )

    assert z_positions == [0, 10, 20]
    assert final_z == 30


def test_run_basic_stack_center_origin(autofocus_thing, mocker):
    """Stack should shift start position when origin is CENTER."""
    stack_params = StackParams(
        stack_dz=10,
        images_to_save=5,
        settling_time=0,
        backlash_correction=0,
        origin=StackOrigin.CENTER,
    )

    capture_params = mocker.Mock()
    capture_params.images_dir = "dummy"
    capture_params.save_resolution = (100, 100)

    autofocus_thing._stage.position = {"x": 0, "y": 0, "z": 100}

    autofocus_thing.capture_stack_image = mocker.Mock(
        return_value=CaptureInfo("id", {"x": 0, "y": 0, "z": 0}, 1)
    )

    autofocus_thing._cam.save_from_memory = mocker.Mock()
    autofocus_thing._cam.clear_buffers = mocker.Mock()
    autofocus_thing._stage.move_relative = mocker.Mock()

    autofocus_thing.run_basic_stack(stack_params, capture_params)

    total_range = 10 * (5 - 1)  # 40
    expected_offset = -total_range // 2  # -20

    # First move should be to CENTER offset (with backlash logic)
    first_call = autofocus_thing._stage.move_relative.call_args_list[0]
    assert first_call.kwargs["z"] == expected_offset


def test_run_basic_stack_backlash_applied(autofocus_thing, mocker, fake_capture):
    """Backlash correction should overshoot and move back."""
    stack_params = StackParams(
        stack_dz=10,
        images_to_save=3,
        settling_time=0,
        backlash_correction=50,
        origin=StackOrigin.START,
    )
    autofocus_thing._stage.position = {"x": 0, "y": 0, "z": 0}
    capture_params = mocker.Mock()
    capture_params.images_dir = "dummy"
    capture_params.save_resolution = (100, 100)

    autofocus_thing.capture_stack_image = mocker.Mock(side_effect=fake_capture)

    autofocus_thing._stage.move_relative = mocker.Mock()
    autofocus_thing._cam.save_from_memory = mocker.Mock()
    autofocus_thing._cam.clear_buffers = mocker.Mock()

    autofocus_thing.run_basic_stack(stack_params, capture_params)

    calls = autofocus_thing._stage.move_relative.call_args_list

    # First call = overshoot
    assert calls[0].kwargs["z"] == -50
    # Second call = move back
    assert calls[1].kwargs["z"] == 50


def test_run_basic_stack_end_origin(autofocus_thing, mocker, fake_capture):
    """END origin should shift stack fully negative before starting."""
    stack_params = StackParams(
        stack_dz=10,
        images_to_save=4,
        settling_time=0,
        backlash_correction=0,
        origin=StackOrigin.END,
    )
    autofocus_thing._stage.position = {"x": 0, "y": 0, "z": 0}
    capture_params = mocker.Mock()
    capture_params.images_dir = "dummy"
    capture_params.save_resolution = (100, 100)

    autofocus_thing.capture_stack_image = mocker.Mock(side_effect=fake_capture)

    autofocus_thing._stage.move_relative = mocker.Mock()
    autofocus_thing._cam.save_from_memory = mocker.Mock()
    autofocus_thing._cam.clear_buffers = mocker.Mock()

    autofocus_thing.run_basic_stack(stack_params, capture_params)

    total_range = 10 * (4 - 1)  # 30

    first_call = autofocus_thing._stage.move_relative.call_args_list[0]
    assert first_call.kwargs["z"] == -total_range
