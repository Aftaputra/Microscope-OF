from flask import abort, url_for

from ..decorators import marshal_with
from ..resource import Resource
from ..schema import Schema
from .. import fields
from ..utilities import description_from_view
from ..spec import update_spec

from openflexure_microscope.common.labthings_core import tasks

from marshmallow import pre_dump


class TaskSchema(Schema):
    _ID = fields.String(data_key="id")
    target_string = fields.String(data_key="function")
    _status = fields.String(data_key="status")
    progress = fields.String()
    data = fields.Raw()
    _return_value = fields.Raw(data_key="return")
    _start_time = fields.String(data_key="start_time")
    _end_time = fields.String(data_key="end_time")

    links = fields.Dict()

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


class TaskList(Resource):
    """
    List and basic documentation for all session tasks
    """

    @marshal_with(TaskSchema(many=True))
    def get(self):
        return tasks.tasks()


class TaskResource(Resource):
    @marshal_with(TaskSchema())
    def get(self, id):
        try:
            print(tasks.dict())
            task = tasks.dict()[id]
        except KeyError:
            return abort(404)  # 404 Not Found

        return task

    @marshal_with(TaskSchema())
    def delete(self, id):
        try:
            task = tasks.dict()[id]
        except KeyError:
            return abort(404)  # 404 Not Found

        task.terminate()

        return task
