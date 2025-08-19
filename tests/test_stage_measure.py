"""File contains unit tests for stage_measure."""

import pytest
from openflexure_microscope_server.things import stage_measure as sm
from .mock_things.mock_csm import MockCSMThing
from .mock_things.mock_stage import MockStageThing

stage_mock = MockStageThing()
csm_mock = MockCSMThing()


def test_generate_move_dicts():
    """Check that the dictionary generated for moves is correct."""
    mock_perc = 50
    mock_res = [820, 616]
    mock_dir = 1
    mock_dict = sm._generate_move_dicts(
        fov_perc=mock_perc, stream_resolution=mock_res, direction=mock_dir
    )
    expected_dict = {"x": 410, "y": 308}
    assert mock_dict == expected_dict


def test_predict_z():
    """Check that the prediction for the next z position is correct."""
    mock_positions = [
        {"x": 0, "y": 0, "z": 42},
        {"x": 727, "y": 2, "z": 154},
        {"x": 1454, "y": 4, "z": 228},
        {"x": 2181, "y": 6, "z": 351},
        {"x": 2908, "y": 8, "z": 509},
        {"x": 3635, "y": 10, "z": 617},
    ]
    mock_axis = "x"
    mock_move = 2908
    mock_z_diff = sm._predict_z(
        positions=mock_positions,
        axis=mock_axis,
        relative_move=mock_move,
        stage=stage_mock,
        csm=csm_mock,
    )
    expected_z_diff = 1343.1625053206606
    assert mock_z_diff == expected_z_diff


def test_parasitic_detect():
    """Check that the parasitic error is raised correctly."""
    mock_delta = 100
    mock_max = 50
    with pytest.raises(sm.ParasiticMotionError):
        sm._parasitic_detect(delta=mock_delta, max_allowed_delta=mock_max)


def test_collate_data():
    """Check that the data is being collected and calculated correctly."""
    mock_data = {
        "positive x": {"final_position": {"x": 100}},
        "negative x": {"final_position": {"x": 50}},
        "positive y": {"final_position": {"y": 100}},
        "negative y": {"final_position": {"y": 50}},
    }

    mock_step_range = [50, 50]
    mock_time = 123
    mock_dict = sm._collate_data(data=mock_data, time=mock_time, csm=MockCSMThing)

    assert mock_dict["Step Range"] == mock_step_range
