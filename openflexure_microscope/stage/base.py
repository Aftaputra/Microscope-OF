from abc import ABCMeta, abstractmethod

import numpy as np
from labthings import StrictLock


class BaseStage(metaclass=ABCMeta):
    """
    Attributes:
        lock (:py:class:`labthings.StrictLock`): Strict lock controlling thread
            access to camera hardware
    """

    def __init__(self):
        self.lock = StrictLock(name="Stage", timeout=None)

    @abstractmethod
    def update_settings(self, config: dict):
        """Update settings from a config dictionary"""

    @abstractmethod
    def read_settings(self):
        """Return the current settings as a dictionary"""

    @property
    @abstractmethod
    def state(self):
        """The general state dictionary of the board."""

    @property
    @abstractmethod
    def configuration(self):
        """The general stage configuration."""

    @property
    @abstractmethod
    def n_axes(self):
        """The number of axes this stage has."""

    @property
    @abstractmethod
    def position(self):
        """The current position, as a list"""

    @property
    def position_map(self):
        return {"x": self.position[0], "y": self.position[1], "z": self.position[2]}

    @property
    @abstractmethod
    def backlash(self):
        """Get the distance used for backlash compensation."""

    @backlash.setter
    @abstractmethod
    def backlash(self):
        """Set the distance used for backlash compensation."""

    @abstractmethod
    def move_rel(self, displacement: list, axis=None, backlash=True):
        """Make a relative move, optionally correcting for backlash.
        displacement: integer or array/list of 3 integers
        backlash: (default: True) whether to correct for backlash.
        """

    @abstractmethod
    def move_abs(self, final, **kwargs):
        """Make an absolute move to a position"""

    @abstractmethod
    def zero_position(self):
        """Set the current position to zero"""

    @abstractmethod
    def close(self):
        """Cleanly close communication with the stage"""

    def scan_linear(self, rel_positions, backlash=True, return_to_start=True):
        """
        Scan through a list of (relative) positions (generator fn)
        rel_positions should be an nx3-element array (or list of 3 element arrays).
        Positions should be relative to the starting position - not a list of relative moves.
        backlash argument is passed to move_rel
        if return_to_start is True (default) we return to the starting position after a
        successful scan.  NB we always attempt to return to the starting position if an
        exception occurs during the scan..
        """
        starting_position = self.position
        rel_positions = np.array(rel_positions)
        assert rel_positions.shape[1] == 3, ValueError(
            "Positions should be 3 elements long."
        )
        try:
            self.move_rel(rel_positions[0], backlash=backlash)
            yield 0

            for i, step in enumerate(np.diff(rel_positions, axis=0)):
                self.move_rel(step, backlash=backlash)
                yield i + 1
        except Exception as e:
            return_to_start = True  # always return to start if it went wrong.
            raise e
        finally:
            if return_to_start:
                self.move_abs(starting_position, backlash=backlash)

    def scan_z(self, dz, **kwargs):
        """Scan through a list of (relative) z positions (generator fn)
        This function takes a 1D numpy array of Z positions, relative to
        the position at the start of the scan, and converts it into an
        array of 3D positions with x=y=0.  This, along with all the
        keyword arguments, is then passed to ``scan_linear``.
        """
        return self.scan_linear([[0, 0, z] for z in dz], **kwargs)
