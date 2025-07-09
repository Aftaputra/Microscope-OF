#! /usr/bin/env python3
"""This module fires up a server in a subprocess to allow for integration tests.""

These are seperated from the unit tests to stop them artificially inflating the test
coverage. For now this file should be run directly not with a test framework.

These tests are designed to run on CI. They should work on Linux or WSL for local
debugging.
"""

import subprocess
import os
import shutil
from time import sleep

from PIL import Image

import labthings_fastapi as lt

THIS_DIR = os.path.dirname(os.path.realpath(__file__))
WORKING_DIR = os.path.join(THIS_DIR, "working_dir")
REPO_DIR = os.path.dirname(THIS_DIR)
CONFIG_FILE = os.path.join(REPO_DIR, "ofm_config_simulation.json")
SERVER_CMD = ["openflexure-microscope-server", "--fallback", "-c", CONFIG_FILE]


def main():
    """Set up the server, run basic checks, shutdown, check for graceful exit"""
    set_up_working_dir()
    os.chdir(WORKING_DIR)

    try:
        print("Starting server")
        server_process = start_server()
        print("Waiting 15s to ensure started up")
        sleep(15)
        error_if_server_not_started(server_process)

        test_client_connection()

        # This also sleeps for 2s and checks it is still connected
        subscriber_process = subscribe_to_mjpeg_stream()

        server_process.terminate()
        sleep(3)

        check_for_graceful_shudown(server_process)

    finally:
        # Ensure the server and subscriber processes are really dead
        if subscriber_process.poll() is None:
            subscriber_process.kill()
        if server_process.poll() is None:
            server_process.kill()
            raise RuntimeError("Server needed killing at end of test.")


def test_client_connection() -> None:
    """Check a ThingClient can interact with the simulation microscope camera"""
    print("Connecting Python client to microscope, and capturing image")
    cam_client = lt.ThingClient.from_url("http://localhost:5000/camera/")
    img = Image.open(cam_client.grab_jpeg().open())
    print(f"Successfully grabbed image of size {img.size}")
    assert img.size == (800, 600)
    print("Successfully grabbed image from camera mjpeg stream")


def subscribe_to_mjpeg_stream() -> subprocess.Popen:
    """Start a background process subscribed to the mjpeg stream.

    :return: The Popen object for the ongoing process.

    :raises: RuntimeError if the stream is not still connected after 2s
    """
    # Use nohup to stop process hanging up unexpectedly. Explicitly forward stream
    # to /dev/null to keep curl connected.

    curl_command = [
        "nohup",
        "curl",
        "-s",
        "http://localhost:5000/camera/mjpeg_stream",
        ">",
        "/dev/null",
        "2>&1",
    ]

    process = subprocess.Popen(
        curl_command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
        universal_newlines=True,
    )
    os.set_blocking(process.stdout.fileno(), False)

    sleep(2)
    if process.poll() is not None:
        raise RuntimeError(
            "MJPEG Subscriber process is not running. This likley means it could not"
            " stay connected to the stream.\n"
        )
    return process


def set_up_working_dir() -> None:
    """If working dir exists, delete it and make a new one."""
    if os.path.exists(WORKING_DIR):
        shutil.rmtree(WORKING_DIR)
    os.makedirs(WORKING_DIR)


def start_server() -> subprocess.Popen:
    """
    Start the server in a subprocess.

    The server is started in a background thread and all outputs are
    buffered.

    :return: Popen object for the ongoing process
    """
    process = subprocess.Popen(
        SERVER_CMD,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
        universal_newlines=True,
    )
    os.set_blocking(process.stdout.fileno(), False)
    os.set_blocking(process.stderr.fileno(), False)
    return process


def error_if_server_not_started(server_process: subprocess.Popen) -> None:
    """Check the server started up as expected.

    Check the subprocess is running
    Check the logs have no errors
    Read the Logs to check uvicorn is running on http://127.0.0.1:5000

    :param server_process: The Popen object for the the server process.

    :rasies RuntimeError: If the server is not running as expected.
    """

    stdout, stderr = read_process_buffers(server_process)
    output = format_stdout_stderr(stdout, stderr)
    if server_process.poll() is not None:
        raise RuntimeError(f"Server process is not running!\n{output}")

    confirmed_uvicorn_is_running = False
    # Note that logs go to stderr once OFM logging process starts, but if there is an
    # error very early (such as on import) on logs may go to stdout
    for line in stdout + stderr:
        if line.startswith("ERROR:"):
            raise RuntimeError(f"Server started up with error\n{line}\n\n{output}")
        if "Uvicorn running on http://127.0.0.1:5000" in line:
            confirmed_uvicorn_is_running = True

    if not confirmed_uvicorn_is_running:
        raise RuntimeError(
            f"Cannot confirm Uvicorn is running on http://127.0.0.1:5000\n\n{output}"
        )

    # If we reached here Everything is fine! print the logs!
    print("Server is running with following outputs:\n\n")
    print(output)


def check_for_graceful_shudown(server_process: subprocess.Popen) -> None:
    """Check the server shutdown gracefully

    Check the subprocess is not running
    Check the logs have no errors
    Read the Logs to check the shutdown was graceful, rather than killed on Uvicorn
    timeout

    :param server_process: The Popen object for the the server process.

    :rasies RuntimeError: If the server didn't shutdown gracefully.
    """
    stdout, stderr = read_process_buffers(server_process)
    output = format_stdout_stderr(stdout, stderr)
    for line in stdout + stderr:
        if line.startswith("ERROR:"):
            raise RuntimeError(f"Server encountered error\n{line}\n\n{output}")
        if "graceful shutdown exceeded" in line:
            # This should be logged as an ERROR. This check is belts and braces.
            raise RuntimeError(f"Server failed to shutdown gracefully.\n\n{output}")


def read_process_buffers(process: subprocess.Popen) -> tuple[list[str], list[str]]:
    """Return STDOUT and STDERR from a process"""
    stdout = []
    stderr = []

    while line := process.stdout.readline():
        stdout.append(line)

    while line := process.stderr.readline():
        stderr.append(line)

    return stdout, stderr


def format_stdout_stderr(stdout: list[str], stderr: list[str]) -> str:
    """Return a ready to print format for stdout and stderr"""
    text = ""
    if stdout:
        text += "**STDOUT**\n" + "".join(stdout) + "\n"
    else:
        text += "**STDOUT IS EMPTY**\n\n"

    if stderr:
        text += "**STDERR**\n" + "".join(stderr) + "\n"
    else:
        text += "**STDERR IS EMPTY**\n\n"
    return text


if __name__ == "__main__":
    main()
