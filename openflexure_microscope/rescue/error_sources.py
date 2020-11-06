class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class Source:
    def __init__(self, message):
        self._message = message

    @property
    def message(self):
        return self._message


class WarningSource:
    def __init__(self, message):
        self.message = message

    @property
    def message(self):
        print(bcolors.WARNING + self._message + bcolors.ENDC)


class ErrorSource:
    def __init__(self, message):
        self.message = message

    @property
    def message(self):
        print(bcolors.FAIL + self._message + bcolors.ENDC)