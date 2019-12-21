from flask import abort, url_for

from openflexure_microscope.common.flask_labthings.schema import Schema
from openflexure_microscope.common.flask_labthings import fields
from openflexure_microscope.common.labthings_core import tasks
from openflexure_microscope.common.flask_labthings.resource import Resource
from openflexure_microscope.common.flask_labthings.utilities import (
    description_from_view,
)

from marshmallow import pre_dump


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


class TaskSchema(Schema):
    _ID = fields.String(data_key="id")
    target_string = fields.String(data_key="function")
    _status = fields.String(data_key="status")
    progress = fields.String()
    data = fields.Raw()
    _return_value = fields.Raw(data_key="return")
    _start_time = fields.String(data_key="start_time")
    _end_time = fields.String(data_key="end_time")

    # TODO: Automate this somewhat
    @pre_dump
    def generate_links(self, data, **kwargs):
        data.links = {
            "self": {
                "href": url_for(TaskResource.endpoint, id=data.id, _external=True),
                "mimetype": "application/json",
                **description_from_view(TaskResource),
            }
        }
        return data


task_schema = TaskSchema()
task_list_schema = TaskSchema(many=True)
