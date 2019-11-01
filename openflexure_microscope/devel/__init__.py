"""
Convenience imports for developers.

Here we include some classes used frequently in plugin development, 
as well as some Flask imports to simplify API route development
"""

# Plugin classes
from openflexure_microscope.plugins import MicroscopePlugin
from openflexure_microscope.api.v1.views import MicroscopeViewPlugin
from openflexure_microscope.api.utilities import JsonResponse

# Task management
from openflexure_microscope.common.tasks import current_task, update_task_progress, update_task_data, taskify

# Exceptions
from openflexure_microscope.exceptions import TaskDeniedException

# Flask things
from flask import abort, escape, jsonify, Response, request
