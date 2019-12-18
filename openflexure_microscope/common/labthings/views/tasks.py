import logging
from flask import abort, request, redirect, url_for, send_file, jsonify

from openflexure_microscope.api.utilities import get_bool, JsonResponse

from openflexure_microscope.common.labthings.schema import Schema
from openflexure_microscope.common.labthings import fields
from openflexure_microscope.common.labthings.resource import Resource

from openflexure_microscope.common import tasks


class TaskSchema(Schema):
    _ID = fields.String(data_key="id")
    target_string = fields.String(data_key="function")
    _status = fields.String(data_key="status")
    progress = fields.String()
    data = fields.Raw()
    _return_value = fields.Raw(data_key="return")
    _start_time = fields.String(data_key="start_time")
    _end_time = fields.String(data_key="end_time")

    # TODO: Add HTTP methods
    links = fields.Hyperlinks(
        {
            "self": {
                "href": fields.AbsoluteUrlFor("TaskResource", id="<id>"),
                "mimetype": "application/json",
            }
        }
    )


task_schema = TaskSchema()
task_list_schema = TaskSchema(many=True)


class TaskList(Resource):
    def get(self):
        return task_list_schema.jsonify(tasks.tasks())


class TaskResource(Resource):
    def get(self, id):
        try:
            task = tasks.dict()[id]
        except KeyError:
            return abort(404)  # 404 Not Found

        # Return task state
        return task_schema.jsonify(task)

    def delete(self, id):
        try:
            task = tasks.dict()[id]
        except KeyError:
            return abort(404)  # 404 Not Found

        task.terminate()

        return task_schema.jsonify(task)
