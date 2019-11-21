import logging
from openflexure_microscope.common.tasks import (
    tasks,
    states,
    taskify,
    cleanup_tasks,
    remove_task,
)

# DEPRECATED
class TaskOrchestrator:
    """
    DEPRECATED: Class responsible for spawning threaded tasks, and storing their returns.
    A microscope should contain exactly one instance of `TaskOrchestrator`.

    Attributes:
        tasks (list): List of `Task` objects

    """

    @property
    def tasks(self):
        logging.warning(
            "TaskOrchestrator class is deprecated. Please use common.tasks.tasks().values() instead."
        )
        return tasks().values()

    @property
    def state(self):
        """
        Returns a list of dictionary representations of all tasks in the session.
        """
        logging.warning(
            "TaskOrchestrator class is deprecated. Please use common.tasks.tasks() instead."
        )
        return states()

    def task_from_id(self, task_id: str):
        """
        Returns a particular task object with the specified `task_id`.
        """
        return tasks()[task_id]

    def start(self, function, *args, **kwargs):
        """
        Attach and start a new long-running task, if allowed by `start_condition()`.
        Returns an instance of :py:class:`openflexure_microscope.task.Task`, which can be used to check the state
        or eventual return of the task.

        Args:
            function (function): The target function to run in the background
            args, kwargs: Arguments that will be passed to `function` at runtime.
        """
        logging.warning(
            "TaskOrchestrator class is deprecated. Please use common.tasks.taskify() instead."
        )
        return taskify(function)(*args, **kwargs)

    def clean(self):
        """
        Remove all inactive tasks from the task array.
        This will remove tasks that either finished or never started.
        """
        logging.warning(
            "TaskOrchestrator class is deprecated. Please use common.tasks.cleanup_tasks() instead."
        )
        cleanup_tasks()

    def delete(self, task_id: str):
        """
        Delete a given task by ID, only if task is not currently running.
        """
        logging.warning(
            "TaskOrchestrator class is deprecated. Please use common.tasks.remove_task() instead."
        )
        remove_task(task_id)
