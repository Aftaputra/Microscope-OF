"""Tests for ScanWorkflow things."""

import itertools
import logging

import pytest
from pydantic import BaseModel

import labthings_fastapi as lt
from labthings_fastapi.testing import create_thing_without_server

from openflexure_microscope_server.scan_planners import SmartSpiral
from openflexure_microscope_server.stitching import StitchingSettings
from openflexure_microscope_server.things.autofocus import SmartStackParams
from openflexure_microscope_server.things.camera_stage_mapping import csm_img_to_stage
from openflexure_microscope_server.things.scan_workflows import (
    HistoScanSettingsModel,
    HistoScanWorkflow,
    ScanWorkflow,
)
from openflexure_microscope_server.ui import PropertyControl


def test_partial_base_classes():
    """Create a partial class and check it raises the correct errors."""

    class MinimalSettings(BaseModel):
        """Some minimal settings for a workflow that doesn't work."""

        foo: str = "bar"

    class BadWorkflow(ScanWorkflow[MinimalSettings]):
        """Can initialise. Other properties and methods error."""

        display_name: str = lt.property(default="Bad Workflow", readonly=True)

    bad_workflow = create_thing_without_server(BadWorkflow)

    settings = MinimalSettings()
    with pytest.raises(NotImplementedError):
        bad_workflow.check_before_start(settings)

    with pytest.raises(NotImplementedError):
        bad_workflow.ready

    with pytest.raises(NotImplementedError):
        bad_workflow.all_settings("Fake Dir")

    with pytest.raises(NotImplementedError):
        bad_workflow.pre_scan_routine(settings)

    with pytest.raises(NotImplementedError):
        bad_workflow.new_scan_planner(settings, position={"x": 0, "y": 0, "z": 0})

    with pytest.raises(NotImplementedError):
        bad_workflow.acquisition_routine(settings, xyz_pos=[0, 0, 0])

    with pytest.raises(NotImplementedError):
        bad_workflow.settings_ui


@pytest.fixture
def histo_workflow():
    """Return a HistoScanWorkflow thing with slots mocked."""
    return create_thing_without_server(HistoScanWorkflow, mock_all_slots=True)


# Use itertools to iterate over every true/false permutation
@pytest.mark.parametrize(
    ("csm_calibrated", "skip_background", "bg_ready"),
    itertools.product([True, False], repeat=3),
)
def test_histo_workflow_ready(
    histo_workflow, csm_calibrated, skip_background, bg_ready, caplog
):
    """Check ready property and the pre-run check work for each permutation."""
    histo_workflow._csm.calibration_required = not csm_calibrated
    histo_workflow.skip_background = skip_background
    histo_workflow._background_detector.ready = bg_ready

    if not csm_calibrated:
        # For all permutations not ready if CSM isn't calibrated.
        assert not histo_workflow.ready
        with pytest.raises(
            RuntimeError, match="Camera Stage Mapping is not calibrated."
        ):
            histo_workflow.check_before_start("scan_name")
    elif not skip_background:
        # CSM is ready and background is not skipped: Always ready, but warns on check
        assert histo_workflow.ready
        with caplog.at_level(logging.WARNING):
            histo_workflow.check_before_start("scan_name")
        assert len(caplog.records) == 1
    elif not bg_ready:
        # Skipping background, but detector not ready. Raises error
        assert not histo_workflow.ready
        with pytest.raises(RuntimeError, match="Background is not set"):
            histo_workflow.check_before_start("scan_name")
    else:
        # Finally CSM calibrated, skipping background, and detector ready: This is
        # ready and should not warn.
        assert histo_workflow.ready
        with caplog.at_level(logging.WARNING):
            histo_workflow.check_before_start("scan_name")
        assert len(caplog.records) == 0


def test_histo_workflow_settings_generation(histo_workflow, mocker):
    """Check the settings models generate as expected."""
    mocker.patch.object(
        histo_workflow, "_calc_displacement_from_overlap", return_value=(123, 456)
    )
    workflow_settings, stitching_settings = histo_workflow.all_settings("/this/img_dir")
    ## Check type
    assert isinstance(workflow_settings, HistoScanSettingsModel)
    assert isinstance(stitching_settings, StitchingSettings)
    assert isinstance(workflow_settings.smart_stack_params, SmartStackParams)

    # Check stitching defaults
    assert stitching_settings.correlation_resize == 0.5
    assert stitching_settings.overlap == 0.45
    # Check some workflow defaults
    assert workflow_settings.overlap == 0.45
    assert workflow_settings.max_dist == 45000
    assert workflow_settings.skip_background
    assert workflow_settings.smart_stack_params.stack_dz == 50
    assert workflow_settings.smart_stack_params.images_to_save == 1
    assert workflow_settings.smart_stack_params.min_images_to_test == 9
    # Check values from calculating overlap are as expected (from above mock)
    assert workflow_settings.dx == 123
    assert workflow_settings.dy == 456
    # And that the input image dir is passed to stack the stack parameter for saving
    assert workflow_settings.capture_params.images_dir == "/this/img_dir"


def test_histo_workflow_settings_generation_equal_overlap(histo_workflow, mocker):
    """Check that setting x and y equal behaves as expected."""
    mocker.patch.object(
        histo_workflow, "_calc_displacement_from_overlap", return_value=(123, 456)
    )

    # Different when False
    histo_workflow.equal_distances = False
    workflow_settings, _stitching_settings = histo_workflow.all_settings(
        "/this/img_dir"
    )

    assert workflow_settings.dx == 123
    assert workflow_settings.dy == 456

    # Same when set True
    histo_workflow.equal_distances = True
    workflow_settings, _stitching_settings = histo_workflow.all_settings(
        "/this/img_dir"
    )

    assert workflow_settings.dx == 123
    assert workflow_settings.dy == 123


# A CSM that is "normal" changing from camera maxtrix coordinates (y,x) to normal
# (x, y) coordinates
CSM_NORMAL = [
    [0.02, 0.25],
    [0.25, 0.01],
]
# A CSM that is "normal" changing from camera maxtrix coordinates (y,x) to normal
# (x, y) coordinates, but the output y sign is flipped.
CSM_FLIP_Y = [
    [0.02, -0.25],
    [0.25, 0.01],
]
# A CSM that is for a rotated compared to normal camera changing from camera maxtrix
#  thus dx (the x motor) controls y and the y motor controls x
CSM_ROTATED = [
    [0.25, 0.02],
    [0.01, 0.25],
]


@pytest.mark.parametrize(
    ("csm_matrix", "overlap", "expected_steps"),
    [
        (CSM_NORMAL, 0.5, (100, 75)),
        (CSM_NORMAL, 0.25, (150, 112)),
        (CSM_FLIP_Y, 0.5, (100, -75)),
        (CSM_FLIP_Y, 0.25, (150, -112)),
        (CSM_ROTATED, 0.5, (75, 100)),
        (CSM_ROTATED, 0.25, (112, 150)),
    ],
)
def test_histo_calculate_overlap(csm_matrix, overlap, expected_steps, histo_workflow):
    """Check the dx and dy values are as expected for given overlap and matrix.

    Note that the matrices on the dominant axes all have 0.25 magnitude. And the
    mock camera is set to be 800px in x and 600px in y. For 0 overlap the movement
    should be dx of 200 (due to the 0.25 factor).
    """

    def apply_csm(x: float, y: float, **_kwargs: float) -> dict[str, int]:
        """Convert image coordinates to stage coordinates."""
        return csm_img_to_stage(csm_matrix, x=x, y=y)

    histo_workflow._csm.convert_image_to_stage_coordinates.side_effect = apply_csm

    # First check this error if CSM isn't calibrated:
    histo_workflow._csm.calibration_required = True
    histo_workflow._csm.image_resolution = None
    with pytest.raises(RuntimeError, match="CSM not set"):
        histo_workflow._calc_displacement_from_overlap(0.25)

    histo_workflow._csm.calibration_required = False
    # the img resolution is in matrix coords, so (y, x) not (x, y)
    histo_workflow._csm.image_resolution = (600, 800)
    dx, dy = histo_workflow._calc_displacement_from_overlap(overlap)
    assert (dx, dy) == expected_steps


def test_histo_pre_scan_routine(histo_workflow, mocker):
    """Check the pre-scan routine does autofocusses."""
    # Rather than create a whole Setting class, just create a mock with the value
    # we need set
    mock_settings = mocker.Mock()
    mock_settings.autofocus_params.dz = 1234
    # Run the function
    histo_workflow.pre_scan_routine(mock_settings)
    # Check the autofocus was run using the mocked slot.
    assert histo_workflow._autofocus.looping_autofocus.call_count == 1
    call_kwargs = histo_workflow._autofocus.looping_autofocus.call_args.kwargs
    assert call_kwargs["dz"] == 1234
    assert call_kwargs["start"] == "centre"


def test_histo_new_scan_planner(histo_workflow, mocker):
    """Check the pre-scan routine does autofocusses."""
    # Rather than create a whole Setting class, just create a mock with the 3 values
    # we need set
    mock_settings = mocker.Mock()
    mock_settings.dx = 666
    mock_settings.dy = 999
    mock_settings.max_dist = 54321

    planner = histo_workflow.new_scan_planner(
        mock_settings, position={"x": 1, "y": 2, "z": 3}
    )
    assert isinstance(planner, SmartSpiral)
    # Check the settings were read
    assert planner._dx == 666
    assert planner._dy == 999
    assert planner._max_dist == 54321


def test_histo_acquisition_with_background_detected(histo_workflow, mocker, caplog):
    """If background is detected it should return without a stack."""
    # Mocking for settings as above
    mock_settings = mocker.Mock()
    mock_settings.skip_background = True

    histo_workflow._background_detector.image_is_sample.return_value = (
        False,
        "totally empty",
    )

    with caplog.at_level(logging.INFO):
        imaged, focus_height = histo_workflow.acquisition_routine(
            mock_settings, xyz_pos=(1, 2, 3)
        )

    # Check returns
    assert imaged is False
    assert focus_height is None  # None meaning not focussed
    # Check there is a log explaining what happened
    assert len(caplog.records) == 1
    assert caplog.records[0].message == "Skipping (1, 2, 3) as it is totally empty."
    assert caplog.records[0].levelname == "INFO"

    # And that smart stack never ran
    assert histo_workflow._autofocus.run_smart_stack.call_count == 0


def test_histo_acquisition_not_skipping_background(histo_workflow, mocker, caplog):
    """Check when not skipping background an image is always saved."""
    # Mocking for settings as above
    mock_settings = mocker.Mock()
    mock_settings.skip_background = False
    mock_settings.smart_stack_params = SmartStackParams(
        stack_dz=5,
        images_to_save=3,
        min_images_to_test=3,
        save_on_failure=True,
        check_turning_points=True,
    )

    # Set up background detector to say it is empty, this shouldn't stop stacking.
    histo_workflow._background_detector.image_is_sample.return_value = (
        False,
        "totally empty",
    )

    with caplog.at_level(logging.INFO):
        # First set smart stack to report failure
        histo_workflow._autofocus.run_smart_stack.return_value = (False, 123)
        imaged, focus_height = histo_workflow.acquisition_routine(
            mock_settings, xyz_pos=(1, 2, 3)
        )
        # Check return
        assert imaged is True  # Always images if not skipping background
        assert focus_height is None  # None meaning didn't focus

        # And again reporting a successful stack
        histo_workflow._autofocus.run_smart_stack.return_value = (True, 123)
        imaged, focus_height = histo_workflow.acquisition_routine(
            mock_settings, xyz_pos=(1, 2, 3)
        )
        # Check return
        assert imaged is True  # Always images if not skipping background
        assert focus_height == 123

    # Should never warn
    assert len(caplog.records) == 0

    # And that smart stack never ran
    assert histo_workflow._autofocus.run_smart_stack.call_count == 2


def test_histo_acquisition_on_sample(histo_workflow, mocker, caplog):
    """Check when skipping background, but background not detected."""
    # Mocking for settings as above
    mock_settings = mocker.Mock()
    mock_settings.skip_background = True
    mock_settings.smart_stack_params = SmartStackParams(
        stack_dz=5,
        images_to_save=3,
        min_images_to_test=3,
        save_on_failure=False,
        check_turning_points=True,
    )

    # Set up background detector to say there is sample.
    histo_workflow._background_detector.image_is_sample.return_value = (True, None)

    with caplog.at_level(logging.INFO):
        # First set smart stack to report failure
        histo_workflow._autofocus.run_smart_stack.return_value = (False, 123)
        imaged, focus_height = histo_workflow.acquisition_routine(
            mock_settings, xyz_pos=(1, 2, 3)
        )
        # Check return:
        # Don't save failed stack when skipping background, assume it is actually
        # background
        assert imaged is False
        assert focus_height is None  # None meaning didn't focus

        # And again reporting a successful stack
        histo_workflow._autofocus.run_smart_stack.return_value = (True, 123)
        imaged, focus_height = histo_workflow.acquisition_routine(
            mock_settings, xyz_pos=(1, 2, 3)
        )
        # Check return
        assert imaged is True  # Always images if not skipping background
        assert focus_height == 123

    # Should never warn
    assert len(caplog.records) == 1
    expected_message = "Stack failed at (1, 2, 3). Treating as background."
    assert caplog.records[0].message == expected_message
    assert caplog.records[0].levelname == "INFO"

    # And that smart stack never ran
    assert histo_workflow._autofocus.run_smart_stack.call_count == 2


def test_histo_workflow_settings_ui(histo_workflow):
    """Check that the workflow specifies the expected controls."""
    ui = histo_workflow.settings_ui

    assert len(ui) == 8
    for element in ui:
        assert isinstance(element, PropertyControl)

    names = [el.property_name for el in ui]
    expected_names = [
        "overlap",
        "stack_images_to_save",
        "stack_min_images_to_test",
        "stack_dz",
        "autofocus_dz",
        "max_range",
        "skip_background",
        "equal_distances",
    ]
    assert names == expected_names
