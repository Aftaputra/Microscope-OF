from threading import Thread
from functools import wraps
import datetime
import time
import uuid

from openflexure_microscope.exceptions import TaskDeniedException
from openflexure_microscope.utilities import entry_by_id

class TaskOrchestrator:
    def __init__(self):
        """
        Class responsible for spawning threaded tasks, and storing their returns.
        A microscope should contain exactly one instance of `TaskOrchestrator`.
        """
        self.tasks = []  #: list: List of `Task` objects

    @property
    def state(self):
        """
        Returns a list of dictionary representations of all tasks in the session.
        """
        return [task.state for task in self.tasks]

    def task_from_id(self, task_id: str):
        """
        Returns a particular task object with the specified `task_id`.
        """
        return entry_by_id(task_id, self.tasks)

    def start(self, function: function, *args, **kwargs):
        """
        Attach and start a new long-running task, if allowed by `start_condition()`.
        Returns an instance of :py:class:`openflexure_microscope.task.Task`, which can be used to check the state
        or eventual return of the task.
    
        Args:
            function (function): The target function to run in the background
            *args, **kwargs: Arguments that will be passed to `function` at runtime.
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
        Currently always allows tasks to start, as locks determine access to hardware.
        """
        #return not any([task._running for task in self.tasks])
        return True


class Task:
    def __init__(self, task, *args, **kwargs):
        """
        Class responsible for running a task function in a thread, and handling return or errors.
        Tasks should be created by an instance of :py:class:`openflexure_microscope.task.TaskOrchestrator`.
        """
        # The task long-running method
        self.task = task  #: function: Function to be called in the task thread.
        self.args = args  #: Positional arguments to be passed to the task function.
        self.kwargs = kwargs  #: Keyword arguments to be passed to the task function.

        self._running = False  #: bool: If task is currently running
        
        self.id = uuid.uuid4().hex  #: str: Unique ID for the task

        self.state = {
            'id': self.id,
            'status': 'idle',
            'return': None,
            'start_time': None,
            'end_time': None,
        }  #: dict: Dictionary describing the full state of the task. `status` will be one of 'idle'', 'running', 'error', or 'success'. `return` eventually holds the return value of the task function.

    def process(self, f):
        """
        Wraps the target function to handle recording `status` and `return` to `state`.
        """
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
        """
        Records the task start and end times to `state`, and runs the task wrapped in `process`.
        """
        self.state['start_time'] = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        self.process(self.task)(*self.args, **self.kwargs)
        self._running = False
        self.state['end_time'] = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")

    def start(self):  # Start and draw
        """
        Spawns a thread, and starts `run()` in that thread.
        """
        # If not already running
        if not self._running:
            self._running = True  # Set start command
            thread = Thread(target=self.run)  # Define thread
            thread.daemon = True  # Stop this thread when main thread closes
            thread.start()  # Start thread