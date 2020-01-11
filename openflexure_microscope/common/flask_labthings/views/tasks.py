from flask import abort, url_for

from ..decorators import marshal_with, ThingProperty
from ..resource import Resource
from ..schema import TaskSchema

from openflexure_microscope.common.labthings_core import tasks


@ThingProperty
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
