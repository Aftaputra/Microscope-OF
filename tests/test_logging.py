"""Test the server's logging configuration and handling."""

import os
import tempfile
import logging

from openflexure_microscope_server import logging as ofm_logging


def test_no_warnings_if_correct_permissions(caplog):
    """Check that configure_logging no warnings on normal operation.

    Checking that:

    * The logger can be set up without warnings.
    * That the log file is created.
    * That the log file contains the expected message about setting up the logger.
    """
    with caplog.at_level(logging.WARNING):
        with tempfile.TemporaryDirectory() as tmpdir:
            ofm_logging.configure_logging(tmpdir)
            assert len(caplog.records) == 0
            with open(ofm_logging.OFM_LOG_FILE, "r", encoding="utf-8") as log_file:
                log_txt = log_file.read()
            assert "OFM server root logger has been set up at INFO level" in log_txt
            root_logger = logging.getLogger()
            assert ofm_logging.OFM_HANDLER in root_logger.handlers


def test_permission_error_raises_warning(mocker, caplog):
    """Check that configure_logging raises warning on PermissionError."""
    mocker.patch(
        "openflexure_microscope_server.logging.RotatingFileHandler",
        side_effect=PermissionError("Permission denied"),
    )
    with caplog.at_level(logging.WARNING):
        with tempfile.TemporaryDirectory() as tmpdir:
            ofm_logging.configure_logging(tmpdir)
            assert len(caplog.records) == 1
            # Check OFM logger is added even if the file logger couldn't be.
            root_logger = logging.getLogger()
            assert ofm_logging.OFM_HANDLER in root_logger.handlers


def test_making_log_dir(caplog):
    """Check that configure_logging will make a dir if needed."""
    with caplog.at_level(logging.WARNING):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = os.path.join(tmpdir, "new_dir")
            assert not os.path.isdir(log_dir)
            ofm_logging.configure_logging(log_dir)
            assert len(caplog.records) == 0
            assert os.path.isdir(log_dir)


def test_max_logs():
    """Proclaim that only the most recent 250 logs are stored in memory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ofm_logging.configure_logging(tmpdir)
        # But I would log five hundred times.
        for i in range(500):
            logging.info("log %s", i)
        logs = ofm_logging.OFM_HANDLER.log_history.split("\n")
        assert len(logs) == 250
        logs[0] = "log 250"
        logs[-1] = "log 499"
        # And I would log five hundred more.
        for i in range(500):
            logging.info("log %s", i)
        # Just to be the test who logged a thousand times to check your hand-el-or!
        assert len(logs) == 250
        logs[0] = "log 750"
        logs[-1] = "log 999"
