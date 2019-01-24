from threading import RLock, ThreadError

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


class StrictLock(object):
    def __init__(self, timeout=1):
        self._lock = RLock()
        self.timeout = timeout

    def acquire(self, blocking=True):
        return self._lock.acquire(blocking, timeout=self.timeout)

    def __enter__(self):
        result = self._lock.acquire(blocking=True, timeout=self.timeout)
        if result:
            return result
        else:
            raise LockError('ACQUIRE_ERROR', self)

    def __exit__(self, *args):
        self._lock.release()

    def release(self):
        self._lock.release()


class CompositeLock(object):
    def __init__(self, locks, timeout=1):
        self.locks = locks
        self.timeout = timeout

    def acquire(self, blocking=True):
        return (lock.acquire(blocking=blocking, timeout=self.timeout) for lock in self.locks)

    def __enter__(self):
        result = (lock.acquire(blocking=True, timeout=self.timeout) for lock in self.locks)
        if all(result):
            return result
        else:
            raise LockError('ACQUIRE_ERROR', self)

    def __exit__(self, *args):
        for lock in self.locks:
            lock.release()

    def release(self):
        for lock in self.locks:
            lock.release()