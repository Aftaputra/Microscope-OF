from openflexure_microscope.api.v1.views import MethodView
from flask import jsonify, abort, Blueprint

from openflexure_microscope.common import tasks


class TaskListAPI(MethodView):
    def get(self):
        """
        Get list of long-running tasks.

        .. :quickref: Tasks; Get collection of tasks

        **Example response**:

        .. sourcecode:: http

          HTTP/1.1 200 OK
          Vary: Accept
          Content-Type: application/json

          [
            {
                "end_time": "2019-01-23 16-33-33", 
                "id": "db13a66787e1419bb06b1504e4d80b0c", 
                "return": [
                0.848622546386467, 
                0.6106785018091292, 
                ], 
                "start_time": "2019-01-23 16-33-13", 
                "status": "success"
            }, 
            {
                "end_time": null, 
                "id": "df46558cc8844924821bd0181881871e", 
                "return": null, 
                "start_time": "2019-01-23 16-34-54", 
                "status": "running"
            }
          ]

        :>header Accept: application/json
        :query include_unavailable: return json representations of captures that have been completely deleted

        :>header Content-Type: application/json
        """

        data = tasks.states()

        return jsonify(data)

    def delete(self):
        """
        Clean list of long-running tasks (running tasks persist).

        .. :quickref: Tasks; Clean collection of tasks

        :>header Accept: application/json

        :>header Content-Type: application/json
        """

        tasks.cleanup_tasks()
        data = tasks.states()

        return jsonify(data)


class TaskAPI(MethodView):
    def get(self, task_id):
        """
        Get JSON representation of a task

        .. :quickref: Tasks; Get task

        **Example request**:

        .. sourcecode:: http

          GET /task/db13a66787e1419bb06b1504e4d80b0c/ HTTP/1.1
          Accept: application/json

        **Example response**:

        .. sourcecode:: http

          HTTP/1.1 200 OK
          Vary: Accept
          Content-Type: application/json

          {
            "end_time": "2019-01-23 16-33-33", 
            "id": "db13a66787e1419bb06b1504e4d80b0c", 
            "return": [
            0.848622546386467, 
            0.6106785018091292, 
            ], 
            "start_time": "2019-01-23 16-33-13", 
            "status": "success"
          }

        """

        try:
            task = tasks.tasks()[task_id]
        except KeyError:
            return abort(404)  # 404 Not Found

        # Return task state
        return jsonify(task.state)

    def delete(self, task_id):
        """
        Terminate a particular task.

        .. :quickref: Tasks; Terminate a task

        :>header Accept: application/json

        :>header Content-Type: application/json
        """

        try:
            task = tasks.tasks()[task_id]
        except KeyError:
            return abort(404)  # 404 Not Found

        task.terminate()

        return jsonify(task.state)


def construct_blueprint(microscope_obj):

    blueprint = Blueprint("task_blueprint", __name__)

    blueprint.add_url_rule("/", view_func=TaskListAPI.as_view("task_list"))

    blueprint.add_url_rule("/<task_id>/", view_func=TaskAPI.as_view("task"))

    return blueprint
