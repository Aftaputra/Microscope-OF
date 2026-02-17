"""Utilities for managing CV2 cameras."""

import sys

import cv2

if sys.platform.startswith("win"):
    BACKEND = cv2.CAP_DSHOW
elif sys.platform.startswith("linux"):
    BACKEND = cv2.CAP_V4L2
elif sys.platform == "darwin":
    BACKEND = cv2.CAP_AVFOUNDATION
else:
    raise RuntimeError("Unsupported platform {sys.platform}")

MAX_CAMERAS = 12


def find_all_cameras() -> list[int]:
    """Find all accessible USB cameras on the device."""
    available = []
    for i in range(MAX_CAMERAS):
        cap = cv2.VideoCapture(i, BACKEND)

        if cap.isOpened():
            available.append(i)
            cap.release()
    return available


def identify_cameras(camera_ids: list[int]) -> dict[str, int]:
    """For a list of camera IDs return a dictionary of name -> ID."""
    # Set default names mapping -d -> camera for easy replacement if names are found.
    name_dict = {n: f"Unknown Camera {n}" for n in camera_ids}
    # If linux try to read video4linux name
    if BACKEND == cv2.CAP_V4L2:
        for camera_id in camera_ids:
            try:
                if not isinstance(camera_id, int):
                    raise TypeError("Camera ID must be an integer.")
                # Linux only so just use direct path.
                path = f"/sys/class/video4linux/video{camera_id}/name"
                with open(path, "r") as f_obj:
                    name_dict[camera_id] = f_obj.read().strip()
            except IOError:
                pass
    # Swap order for return
    return {name: cam_id for cam_id, name in name_dict.items()}
