#! /usr/bin/env python3
"""This module fires up a server in a subprocess to allow for integration tests.""

These are seperated from the unit tests to stop them artificially inflating the test
coverage. For now this file should be run directly not with a test framework
"""

import subprocess
import os
import shutil
from time import sleep


THIS_DIR = os.path.dirname(os.path.realpath(__file__))
WORKING_DIR = os.path.join(THIS_DIR, "working_dir")
REPO_DIR = os.path.dirname(THIS_DIR)
CONFIG_FILE = os.path.join(REPO_DIR, "ofm_config_simulation.json")
CMD = ["openflexure-microscope-server", "--fallback", "-c", CONFIG_FILE]


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

    finally:
        # Ensure the server process is really dead
        if server_process.poll() is None:
            print("Server still running, shutting down.")
            server_process.terminate()
            sleep(2)
            if server_process.poll() is None:
                server_process.kill()
                raise RuntimeError("Server needed killing at end of test.")


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
        CMD,
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
    """

    stdout, stderr = read_process_buffers(server_process)
    output = format_stdout_stderr(stdout, stderr)
    if server_process.poll() is not None:
        raise RuntimeError(f"Server process is not running!\n{output}")

    confirmed_uvicorn_is_running = False
    # Note that logs go to stderr once OFM logging process stars, but if there is an
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
