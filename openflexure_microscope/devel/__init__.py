"""
Convenience imports for developers.

Here we include some classes used frequently in plugin development, 
as well as some Flask imports to simplify API route development
"""

from openflexure_microscope.api.utilities import JsonResponse

# Task management
from labthings.core.tasks import (
    current_task,
    update_task_progress,
    update_task_data,
)


# Flask things
from flask import abort, escape, Response, request


__all__ = [
    "current_task",
    "update_task_progress",
    "update_task_data",
    "abort",
    "escape",
    "Response",
    "request",
]
