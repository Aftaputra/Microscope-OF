## Hardware specific tests for the PiCamera.

These are very slow as they run on hardware. They can be run with:

    pytest hardware-specific-tests

It is essential to stop the server first:

    ofm stop

However, this will not archive the tests in the Git repository for reporting the coverage. For this see the section below on reporting the coverage.

When writing and debugging these unit tests it is often best to run a specific test and to use the `-s` flag to see the print statements. It is also often useful to use `--pdb` to drop you into a python debug session on any failure. For example, you might run:

    /picamera2/test_exposure_time_drift.py::test_exposure_time_saves_and_loads -s --pdb

### Reporting the coverage

To create a coverage report that will be included into the repository run:

    ./picamera_tests.py run

This will create a zip of test results along with hashes of the picamera files and the base camera file. The server will include this overage report if the source files remain the same.