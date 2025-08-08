"""Create a fake CancelHook used instead of a dependency, it cannot be used to cancel!

Certain actions require a CancelHook to be supplied if called directly. The only method
we use from the LabThings CancelHook is ``sleep()``. The CanceHook ``sleep()`` works
exactly like ``time.sleep()`` except with raise an ``InvocationCancelledError`` if the
server receives a cancellation request.

This is just an object with a sleep method.
"""

import time


class MockCancel:
    """A class to use when directly calling an action with CancelHook dependency."""

    def sleep(self, time_in_seconds: float):
        """Sleep for the input number of seconds."""
        time.sleep(time_in_seconds)
