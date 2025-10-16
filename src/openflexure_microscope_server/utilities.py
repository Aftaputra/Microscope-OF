"""Utility functions and classes."""

from typing import TypeVar, Callable, ParamSpec, Optional, Any, Concatenate, Self
import os
import re
import sys
from threading import Thread
import logging
from importlib.metadata import version
import tomllib
from functools import wraps

from pydantic import BaseModel

T = TypeVar("T")
P = ParamSpec("P")

LOGGER = logging.getLogger(__name__)

REPO_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
# Regex for a full commit hash
COMMIT_REGEX = re.compile(r"[0-9a-f]{40}")
# Regex for a reference in the git HEAD file. Group 1 is the path.
REF_REGEX = re.compile(r"^ref:\s(.*)$")


def _is_lock_like(obj: Any) -> bool:
    """Check if an object is a lock.

    Cannot use ``isinstance(obj, threading.RLock)``, may be possible to use
    ``isinstance(obj, threading._RLock)``. But this uses a private method and may
    break. Instead making the check that both "acquire" and "release" exist.
    """
    return hasattr(obj, "acquire") and hasattr(obj, "release")


def requires_lock(
    method: Callable[Concatenate[Self, P], T],
) -> Callable[Concatenate[Self, P], T]:
    """Decorate a class method so that it requires the class lock to run.

    The class should have a reentrant lock with the name ``self._lock``.
    """

    @wraps(method)
    def wrapper(self: Self, *args: P.args, **kwargs: P.kwargs) -> T:
        # Confirm the object the method is attached to has a self._lock property
        if not hasattr(self, "_lock"):
            raise AttributeError(f"{self.__class__.__name__} has no '_lock' attribute")
        # And that it is a reentrant lock.
        if not _is_lock_like(self._lock):
            raise TypeError("requires_lock requires self._lock to be a lock")
        with self._lock:
            return method(self, *args, **kwargs)

    return wrapper


class ErrorCapturingThread(Thread):
    """Subclass of Thread that captures exceptions from the target function.

    It wraps the target function in a try-except block.

    Execution will stop with an unhandled exception, but the exception will not be raised
    until the join method is called. When the join method is called, the exception is
    called in the calling thread.

    This allows for error handling to be performed by the calling thread at the time that
    join is run.
    """

    def __init__(
        self,
        group: Optional[Any] = None,
        target: Optional[Callable[..., Any]] = None,
        name: Optional[str] = None,
        args: tuple[Any, ...] = (),
        kwargs: Optional[dict[str, Any]] = None,
        *,
        daemon: Optional[bool] = None,
    ) -> None:
        """Initialise with the same arguments as Thread."""
        # As all inputs are keywords we need to set the default values for args and kwargs:
        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}

        # Make an empty list for any error.
        # We are only ever going to have one or zero errors, this is an empty
        # list as we need to pass the reference not the value to collect the
        # error. If we could simply make a pointer we would have done that.
        self._error_buffer = []

        # Add the target function end error buffer to the thread to the start of
        # the argument list so they are passed to _wrap_and_catch_errors()
        args = (target, self._error_buffer, *args)
        # Start the thread with _wrap_and_catch_errors() as the target
        super().__init__(
            group=group,
            target=_wrap_and_catch_errors,
            name=name,
            args=args,
            kwargs=kwargs,
            daemon=daemon,
        )

    def join(self, timeout: Optional[float] = None) -> None:
        """Join when the thread is complete.

        If the thread ended due to an unhandled exception, the exception will be raised
        when this method is called.
        """
        super().join(timeout)
        # If there is an error in the error buffer clear the buffer and raise it
        if self._error_buffer:
            err = self._error_buffer[0]
            self._error_buffer = []
            raise err


def _wrap_and_catch_errors(
    target: Callable[..., Any], error_buffer: list, *args: Any, **kwargs: Any
) -> None:
    """Run target function in a try-except block.

    This function is designed only to be used by ErrorCapturingThread.

    It will run a target function in a try-except block catching any exception.
    If an exception is caught it is added to ``error_buffer``.

    :param target: The target function to call
    :param error_buffer: An empty list that is used for returning the exception from
        the thread. It is a list to ensure it is passed by reference.
    :param ``*args``: The arguments for the target function
    :param ``**kwargs``: The Keyword arguments for the target function
    """
    try:
        target(*args, **kwargs)
    except BaseException as e:
        error_buffer.append(e)


# Compiled regular expressions for unsafe characters
# Matches anything that isn't a-z, A-Z, 0-9, _, ., -, :, /, \
_WINDOWS_UNSAFE_PATTERN = re.compile(r"[^a-zA-Z0-9_.\-:/\\]")
# Matches anything that isn't a-z, A-Z, 0-9, _, ., -, \
_POSIX_UNSAFE_PATTERN = re.compile(r"[^a-zA-Z0-9_.\-/]")
# Matches anything that isn't a-z, A-Z, 0-9, _, ., -
_NAME_UNSAFE_PATTERN = re.compile(r"[^a-zA-Z0-9_.\-]")


def make_path_safe(unsafe_path_string: str) -> str:
    """Replace unsafe characters in a file path with underscores, preserving separators.

    This can be used to check that user inputs have not been concatenated into an
    unsafe filepath.

    This ensures compatibility across platforms by preserving only valid characters,
    including path separators (forward slash on POSIX, and forward
    slash/backslash/colon on Windows).

    :param unsafe_path_string: The original path string to sanitise.

    :returns: A version of the input string safe to use as a file path.
    """
    unsafe_character_pattern = (
        _WINDOWS_UNSAFE_PATTERN
        if sys.platform.startswith("win")
        else _POSIX_UNSAFE_PATTERN
    )
    return unsafe_character_pattern.sub("_", unsafe_path_string)


def make_name_safe(unsafe_name_string: str) -> str:
    """Replace unsafe characters in a filename or identifier with underscores.

    This excludes all path separators, ensuring the result is safe to use as a
    standalone filename or identifier component.

    :param unsafe_name_string: The original name string to sanitise.

    :returns: A version of the input string safe to use as a file name or identifier.
    """
    return _NAME_UNSAFE_PATTERN.sub("_", unsafe_name_string)


class VersionData(BaseModel):
    """A BaseModel containing the information about the server version.

    :param version: The version string for the server. Or "Undefined" if there is an
        error.
    :param version_source: Either a Git commit hash, "TOML", "Dist" or in the case of
        an error - "Undefined".
    """

    version: str
    version_source: str


def robust_version_strings() -> VersionData:
    """Return a version string and information on its source.

    Returning a python version string is not without problems. If the package is
    installed in an editable way, often METADATA is never updated. This provides 4
    ways to provide a version string:

    1. If both a Git directory and a pyproject.toml are available. Return the version
        string from the toml file and the git hash from the ``.git`` directory as its
        source.
    2. If a pyproject.toml is available but no Git directory then this is likely an
        installation from source. Return the version string from the toml file and
        return the literal string "TOML" as its source.
    3. If a Git directory is available but no pyproject.toml then something is very
        weird - log an error. Then return "Undefined" as the version string, but still
        return the Git hash as the source.
    4. Finally if neither a Git directory nor a pyproject.toml are available then the
       server has been installed from a distribution package (i.e. a wheel). In this
       case use the standard library function ``importlib.metadata.version`` for the
       version string (prepending a "v") and return "Dist" as its source.

    :returns: a VersionData instance with the version string and source.

    """
    project_toml_path = os.path.join(REPO_DIR, "pyproject.toml")
    git_dir_path = os.path.join(REPO_DIR, ".git")
    has_project_toml = os.path.isfile(project_toml_path)
    has_git_dir = os.path.isdir(git_dir_path)

    if has_project_toml and has_git_dir:
        # .git dir and pyproject.toml available. This is a development
        # installation.
        ver = "v" + _get_version_from_toml(project_toml_path)
        source = _get_hash_from_git_dir(git_dir_path)
    elif has_project_toml:
        # Only pyproject.toml available. Likely installed from source. Check
        # file directly as `importlib.metadata.version` plays badly with editable
        # installs.
        ver = "v" + _get_version_from_toml(project_toml_path)
        source = "TOML"
    elif has_git_dir:
        # Only .git dir, that is weird.
        LOGGER.error(
            "Unexpected installation configuration. Version number cannot be verified."
        )
        ver = "Undefined"
        source = _get_hash_from_git_dir(git_dir_path)
    else:
        # Has neither .git nor pyproject.toml. It is probably installed from wheel.
        # This will be the expected method of packaging in the future. This option
        # is handled last as ``importlib.metadata.version`` can be unreliable if
        # the package is no installed as a distribution package.
        ver = "v" + version("openflexure_microscope_server")
        source = "Dist"
    return VersionData(version=ver, version_source=source)


def _get_hash_from_git_dir(git_dir_path: str) -> str:
    """Get the commit hash from a .git directory directly.

    This function doesn't rely on GIT being on the PATH or even installed. It doesn't
    require any packages outside the Python standard library. It directly inspects the
    .git directory to get the commit hash:

    * If the repository is on a detached HEAD then the hash will be in the file
        .git/HEAD. A detached HEAD is could be from checking out a tag or checking out
        a commit directly.
    * In normal operation .git/HEAD points to a reference or "ref". This ref file
        contains the hash.

    :param git_dir_path: The path to the .git directory.

    :returns: The hash, or "Undefined" if there is any error, errors are logged not
        raised.
    """
    head_path = os.path.join(git_dir_path, "HEAD")
    try:
        with open(head_path, "r", encoding="utf-8") as head_file:
            head = head_file.read()
    except IOError:
        LOGGER.error("Problem opening .git/HEAD")
        return "Undefined"
    # The file HEAD should either be a reference or commit ID.
    if match := COMMIT_REGEX.match(head):
        return match.group(0)
    if match := REF_REGEX.match(head):
        ref_path = os.path.join(git_dir_path, match.group(1))
        return _get_hash_from_git_ref(ref_path)
    LOGGER.error("Unexpected format for .git/HEAD")
    return "Undefined"


def _get_hash_from_git_ref(git_ref_path: str) -> str:
    """Get the commit hash from a ref in the .git directory.

    For more detail see `_get_hash_from_git_dir`

    :param git_ref_path: The full path to the ref file in the .git directory.

    :returns: The hash, or "Undefined" if there is any error, errors are logged not
        raised.
    """
    try:
        with open(git_ref_path, "r", encoding="utf-8") as ref_file:
            ref = ref_file.read()
    except IOError:
        LOGGER.error("Problem opening Git branch reference.")
        return "Undefined"
    if ref_match := COMMIT_REGEX.match(ref):
        return ref_match.group(0)
    LOGGER.error("No hash found in Git ref")
    return "Undefined"


def _get_version_from_toml(toml_path: str) -> str:
    """Get the version string from a pyproject.toml file.

    :param toml_path: The path to the toml file.

    :returns: The version string directly as reported in the toml file, or "Undefined"
        if there is any error, errors are logged not raised.
    """
    try:
        with open(toml_path, "rb") as toml_file:
            toml_dict = tomllib.load(toml_file)
        return toml_dict["project"]["version"]
    except (IOError, ValueError, KeyError):
        LOGGER.error("Problem opening pyproject.toml")
        return "Undefined"


def quadratic(x: float, a: float, b: float, c: float) -> float:
    """Quadratic function. Used for predicting z.

    :param x: The points at which to evaluate the quadratic.
    :param a: The coefficient of x^2.
    :param b: The coefficient of x.
    :param c: The constant coefficient.
    :return: The quadratic, evaluated at each point in ``x``
    """
    return a * x**2 + b * x + c
