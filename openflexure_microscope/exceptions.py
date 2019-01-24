from threading import ThreadError

class TaskDeniedException(Exception):
    pass

class LockError(ThreadError):
    ERROR_CODES = {
        'ACQUIRE_ERROR': "Unable to acquire. Lock in use by another thread.",
        'IN_USE_ERROR': "Lock in use by another thread."
    }

    def __init__(self, code, lock):
        self.code = code
        if code in LockError.ERROR_CODES:
            self.message = LockError.ERROR_CODES[code]
        else:
            self.message = "Unknown error."
        print("{}: {}".format(self.code, self.message))

        ThreadError.__init__(self)