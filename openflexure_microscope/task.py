from threading import Thread
from functools import wraps
import datetime
import time
import uuid

from openflexure_microscope.exceptions import TaskDeniedException
from openflexure_microscope.utilities import entry_by_id

class TaskOrchestrator:
    def __init__(self):
        # List of tasks in the orchestrator
        self.tasks = []

    @property
    def state(self):
        return [task.state for task in self.tasks]

    def task_from_id(self, task_id):
        return entry_by_id(task_id, self.tasks)

    def start(self, function, *args, **kwargs):
        """
        Attach and start a new long-running task, if allowed by `start_condition()`.
        """
        # Create a task object
        task = Task(function, *args, **kwargs)
        
        # If the task isn't allowed to run
        if not self.start_condition(task):
            raise TaskDeniedException("Unable to start this task. Aborting.")
        else:
            self.tasks.append(task)
            task.start()
            return task

    def clean(self):
        """
        Remove all inactive tasks from the task array.
        This will remove tasks that either finished or never started.
        """
        self.tasks = [task for task in self.tasks if task._running]

    def delete(self, task_id):
        """
        Delete a given task by ID, only if task is not currently running.
        """
        success = False

        for task in self.tasks:
            if task.id == task_id and not task._running:
                self.tasks.remove(task)
                success = True

        return success

    def start_condition(self, task_obj):
        """
        Method returning bool describing if a particular task is allowed to run.
        In the future, this will depend on the state of hardware locks?
        Currently just allows a single task at a time.
        """
        return not any([task._running for task in self.tasks])


class Task:
    def __init__(self, task, *args, **kwargs):

        # The task long-running method
        self.task = task
        self.args = args
        self.kwargs = kwargs

        # If task is currently running
        self._running = False
        
        self.id = uuid.uuid4().hex

        self.state = {
            'id': self.id,
            'status': 'idle',
            'return': None,
            'start_time': None,
            'end_time': None,
        }

    def process(self, f):
        def wrapped(*args, **kwargs):
            self.state['status'] = 'running'
            try:
                r = f(*args, **kwargs)
                s = 'success'
            except Exception as e:
                r = e
                s = 'error'
            self.state['return'] = r
            self.state['status'] = s
        return wrapped

    def run(self):
        self.state['start_time'] = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        self.process(self.task)(*self.args, **self.kwargs)
        self._running = False
        self.state['end_time'] = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")

    def start(self):  # Start and draw
        # If not already running
        if not self._running:
            self._running = True  # Set start command
            thread = Thread(target=self.run)  # Define thread
            thread.daemon = True  # Stop this thread when main thread closes
            thread.start()  # Start thread