import logging
import time
from contextlib import contextmanager
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
from labthings import current_action, fields, find_component
from labthings.extensions import BaseExtension
from labthings.views import ActionView, View
from scipy import ndimage

from openflexure_microscope.camera.base import BaseCamera
from openflexure_microscope.devel import abort
from openflexure_microscope.microscope import Microscope
from openflexure_microscope.stage.base import BaseStage
from openflexure_microscope.utilities import set_properties

### Autofocus utilities


class JPEGSharpnessMonitor:
    def __init__(self, microscope: Microscope):
        self.microscope: Microscope = microscope
        self.camera: BaseCamera = microscope.camera
        self.stage: BaseStage = microscope.stage

        self.recording_start_time: Optional[float] = None

        self.stage_positions: List[Tuple[int, int, int]] = []
        self.stage_times: List[float] = []
        self.jpeg_times: List[float] = []
        self.jpeg_sizes: List[int] = []

    def start(self):
        # Log the recording start time
        self.recording_start_time = time.time()

    def stop(self):
        self.camera.stream.stop_tracking()
        self.camera.stream.reset_tracking()

    def focus_rel(self, dz: int, backlash: bool = False, **kwargs) -> Tuple[int, int]:
        # Store the start time and position
        self.camera.stream.start_tracking()
        self.stage_times.append(time.time())
        self.stage_positions.append(self.stage.position)

        # Main move
        self.stage.move_rel((0, 0, dz), backlash=backlash, **kwargs)

        # Store the end time and position
        self.camera.stream.stop_tracking()
        self.stage_times.append(time.time())
        self.stage_positions.append(self.stage.position)

        # Retrieve frame data
        for frame in self.camera.stream.frames:
            # Make timestamp absolute Unix time
            self.jpeg_times.append(frame.time)
            self.jpeg_sizes.append(frame.size)
        # Clear frame data for this move from the stream
        self.camera.stream.reset_tracking()

        # Index of the data for this movement
        data_index: int = len(self.stage_positions) - 2
        # Final z position after move
        final_z_position: int = self.stage_positions[-1][2]
        return data_index, final_z_position

    def move_data(
        self, istart: int, istop: Optional[int] = None
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Extract sharpness as a function of (interpolated) z"""
        if istop is None:
            istop = istart + 2
        jpeg_times: np.ndarray = np.array(self.jpeg_times)  # np.ndarray[float]
        jpeg_sizes: np.ndarray = np.array(self.jpeg_sizes)  # np.ndarray[int]
        stage_times: np.ndarray = np.array(self.stage_times)[
            istart:istop
        ]  # np.ndarray[float]
        stage_zs: np.ndarray = np.array(self.stage_positions)[
            istart:istop, 2
        ]  # np.ndarray[int]
        try:
            start: int = int(np.argmax(jpeg_times > stage_times[0]))
            stop: int = int(np.argmax(jpeg_times > stage_times[1]))
        except ValueError as e:
            if np.sum(jpeg_times > stage_times[0]) == 0:
                raise ValueError(
                    "No images were captured during the move of the stage.  Perhaps the camera is not streaming images?"
                ) from e
            else:
                raise e
        if stop < 1:
            stop = len(jpeg_times)
            logging.debug("changing stop to %s", (stop))
        jpeg_times = jpeg_times[start:stop]
        jpeg_zs: np.ndarray = np.interp(
            jpeg_times, stage_times, stage_zs
        )  # np.ndarray[float]
        return jpeg_times, jpeg_zs, jpeg_sizes[start:stop]

    def sharpest_z_on_move(self, index: int) -> int:
        """Return the z position of the sharpest image on a given move"""
        _, jz, js = self.move_data(index)
        if len(js) == 0:
            raise ValueError(
                "No images were captured during the move of the stage.  Perhaps the camera is not streaming images?"
            )
        return jz[np.argmax(js)]

    def data_dict(self) -> Dict[str, np.ndarray]:
        """Return the gathered data as a single convenient dictionary"""
        data = {}
        for k in ["jpeg_times", "jpeg_sizes", "stage_times", "stage_positions"]:
            data[k] = getattr(self, k)
        return data


@contextmanager
def monitor_sharpness(microscope: Microscope):
    m: JPEGSharpnessMonitor = JPEGSharpnessMonitor(microscope)
    m.start()
    try:
        yield m
    finally:
        m.stop()


def sharpness_sum_lap2(rgb_image: np.ndarray) -> np.float:
    """Return an image sharpness metric: sum(laplacian(image)**")"""
    image_bw: np.float = np.mean(rgb_image, 2)
    image_lap: np.float = ndimage.filters.laplace(image_bw)
    return np.mean(image_lap.astype(np.float) ** 4)


def sharpness_edge(image: np.ndarray) -> np.float:
    """Return a sharpness metric optimised for vertical lines"""
    gray: np.float = np.mean(image.astype(float), 2)
    n: int = 20
    edge: np.ndarray = np.array([[-1] * n + [1] * n])
    return np.sum(
        [np.sum(ndimage.filters.convolve(gray, W) ** 2) for W in [edge, edge.T]]
    )


### Autofocus extension


class AutofocusExtension(BaseExtension):
    def __init__(self):
        super().__init__(
            "org.openflexure.autofocus",
            version="2.0.0",
            description="Actions to move the microscope in Z and pick the point with the sharpest image.",
        )
        self.add_view(
            MeasureSharpnessAPI, "/measure_sharpness", endpoint="measure_sharpness"
        )
        self.add_view(AutofocusAPI, "/autofocus", endpoint="autofocus")
        self.add_view(FastAutofocusAPI, "/fast_autofocus", endpoint="fast_autofocus")
        self.add_view(
            UpDownUpAutofocusAPI, "/updownup_autofocus", endpoint="updownup_autofocus"
        )

        self.add_view(
            MoveAndMeasureAPI, "/move_and_measure", endpoint="move_and_measure"
        )

    def measure_sharpness(
        self, microscope: Microscope, metric_fn: Callable = sharpness_sum_lap2
    ) -> np.float:
        """Measure the sharpness of the camera's current view."""

        if hasattr(microscope.camera, "array") and callable(
            getattr(microscope.camera, "array")
        ):
            return metric_fn(getattr(microscope.camera, "array")(use_video_port=True))
        else:
            raise RuntimeError(f"Object {microscope.camera} has no method `array`")

    def autofocus(
        self,
        microscope: Microscope,
        dz: List[int],
        settle: float = 0.5,
        metric_fn: Callable = sharpness_sum_lap2,
    ) -> Tuple[List[int], List[np.float]]:
        """Perform a simple autofocus routine.
        The stage is moved to z positions (relative to current position) in dz,
        and at each position an image is captured and the sharpness function 
        evaulated.  We then move back to the position where the sharpness was
        highest.  No interpolation is performed.
        dz is assumed to be in ascending order (starting at -ve values)
        """
        camera: BaseCamera = microscope.camera
        stage: BaseStage = microscope.stage

        with set_properties(stage, backlash=256), stage.lock, camera.lock:
            sharpnesses: List[np.float] = []
            positions: List[int] = []

            # Some cameras may not have annotate_text. Reset if it does
            if getattr(camera, "annotate_text"):
                setattr(camera, "annotate_text", "")

            for _ in stage.scan_z(dz, return_to_start=False):
                if current_action() and current_action().stopped:
                    return [], []
                positions.append(stage.position[2])
                time.sleep(settle)
                sharpnesses.append(self.measure_sharpness(microscope, metric_fn))

            newposition: int = positions[int(np.argmax(sharpnesses))]
            stage.move_rel((0, 0, newposition - stage.position[2]))

        return positions, sharpnesses

    def move_and_find_focus(self, microscope: Microscope, dz: int) -> int:
        """Make a relative Z move and return the peak sharpness position"""
        with monitor_sharpness(microscope) as m:
            m.focus_rel(dz)
            return m.sharpest_z_on_move(0)

    def move_and_measure(
        self, microscope: Microscope, dz: int
    ) -> Dict[str, np.ndarray]:
        """Make a relative Z move and return the sharpness data"""
        with monitor_sharpness(microscope) as m:
            m.focus_rel(dz)
            return m.data_dict()

    def fast_autofocus(
        self, microscope: Microscope, dz: int = 2000
    ) -> Dict[str, np.ndarray]:
        """Perform a down-up-down-up autofocus"""
        with microscope.camera.lock, microscope.stage.lock:
            with monitor_sharpness(microscope) as m:
                # Move to (-dz / 2)
                m.focus_rel(-dz / 2)
                # Move to dz while monitoring sharpness
                # i: Sharpness monitor index for this move
                # z: Final z position after move
                i, z = m.focus_rel(dz)
                # Get the z position with highest sharpness from the previous move (index i)
                fz: int = m.sharpest_z_on_move(i)
                # Move all the way to the start so it's consistent
                # Store final absolute z position from this return move
                i, z = m.focus_rel(-dz)
                # Move to the target position fz
                # Can't do absolute move here yet so move by (fz - z)
                m.focus_rel(fz - z)
                # Return all focus data
                return m.data_dict()

    def fast_up_down_up_autofocus(
        self,
        microscope: Microscope,
        dz: int = 2000,
        target_z: int = 0,
        initial_move_up: bool = True,
        mini_backlash: int = 25,
    ) -> Dict[str, np.ndarray]:
        """Autofocus by measuring on the way down, and moving back up with feedback.

        This autofocus method is very efficient, as it only passes the peak once.
        The sequence of moves it performs is:

        1.  Move to the top of the range `dz/2` (can be disabled)

        2.  Move down by `dz` while monitoring JPEG size to find the focus.

        3.  Move back up to the `target_z` position, relative to the sharpest image.

        4.  Measure the sharpness, and compare against the curve recorded in (2) to \\
            estimate how much further we need to go.  Make this move, to reach our \\
            target position.

        Moving back to the target position in two steps allows us to correct for
        backlash, by using the sharpness-vs-z curve as a rough encoder for Z.

        Parameters:
            dz: number of steps over which to scan (optional, default 2000)

            target_z: we aim to finish at this position, relative to focus.  This may 
                be useful if, for example, you want to acquire a stack of images in Z. 
                It is optional, and the default value of 0 will finish at the focus.

            initial_move_up: (optional, default True) set this to `False` to move down
                from the starting position.  Mostly useful if you're able to combine
                the initial move with something else, e.g. moving to the next scan point.

            mini_backlash: (optional, default 25) is a small extra move made in step
                3 to help counteract backlash.  It should be small enough that you
                would always expect there to be greater backlash than this.  Too small
                might slightly hurt accuracy, but is unlikely to be a big issue.  Too big
                may cause you to overshoot, which is a problem.
        """
        with microscope.camera.lock, microscope.stage.lock:
            with monitor_sharpness(microscope) as m:
                # Ensure the MJPEG stream has started
                microscope.camera.start_stream()

                logging.debug("Initial move")
                if initial_move_up:
                    m.focus_rel(dz / 2)
                # move down
                logging.debug("Move down")
                i: int
                z: int
                i, z = m.focus_rel(-dz)
                # now inspect where the sharpest point is, and estimate the sharpness
                # (JPEG size) that we should find at the start of the Z stack
                jz: np.ndarray  # np.ndarray[float]
                js: np.ndarray  # np.ndarray[float]
                _, jz, js = m.move_data(i)
                best_z: int = jz[np.argmax(js)]

                # now move to the start of the z stack
                logging.debug("Move to the start of the z stack")
                i, z = m.focus_rel(
                    best_z + target_z - z + mini_backlash
                )  # takes us to the start of the stack

                # We've deliberately undershot - figure out how much further we should move based on the curve
                logging.debug("Calculate remining movement")
                current_js = m.camera.stream.last.size
                imax: int = int(
                    np.argmax(js)
                )  # we want to crop out just the bit below the peak
                js = js[imax:]  # NB z is in DECREASING order
                jz = jz[imax:]
                inow: int = int(
                    np.argmax(js < current_js)
                )  # use the curve we recorded to estimate our position

                # So, the Z position corresponding to our current sharpness value is zs[inow]
                # That means we should move forwards, by best_z - zs[inow]
                logging.debug("Correction move")
                correction_move: int = best_z + target_z - jz[inow]
                logging.debug(
                    "Fast autofocus scan: correcting backlash by moving %s steps",
                    (correction_move),
                )
                m.focus_rel(correction_move)
                return m.data_dict()


class MeasureSharpnessAPI(View):
    def post(self):
        microscope = find_component("org.openflexure.microscope")

        if not microscope:
            abort(503, "No microscope connected. Unable to measure sharpness.")

        return {"sharpness": self.extension.measure_sharpness(microscope)}


class MoveAndMeasureAPI(ActionView):
    """
    Move the stage and measure dynamic sharpness
    """

    args = {"dz": fields.Int(required=True)}

    def post(self, args):
        microscope = find_component("org.openflexure.microscope")

        if not microscope:
            abort(503, "No microscope connected. Unable to autofocus.")

        if microscope.has_real_stage():
            # Acquire microscope lock with 1s timeout
            with microscope.camera.lock, microscope.stage.lock:
                return self.extension.move_and_measure(microscope, dz=args.get("dz"))

        else:
            abort(503, "No stage connected. Unable to autofocus.")


class AutofocusAPI(ActionView):
    """
    Run a standard autofocus
    """

    args = {"dz": fields.List(fields.Int())}

    def post(self, args):
        microscope = find_component("org.openflexure.microscope")

        if not microscope:
            abort(503, "No microscope connected. Unable to autofocus.")

        # Figure out the range of z values to use
        dz = np.array(args.get("dz", np.linspace(-300, 300, 7)))

        if microscope.has_real_stage():
            logging.debug("Running autofocus...")

            # return a handle on the autofocus task
            return self.extension.autofocus(microscope, dz)

        else:
            abort(503, "No stage connected. Unable to autofocus.")


class FastAutofocusAPI(ActionView):
    """
    Run a fast autofocus
    """

    args = {"dz": fields.Int(missing=2000, example=2000)}

    def post(self, args):
        microscope = find_component("org.openflexure.microscope")

        if not microscope:
            abort(503, "No microscope connected. Unable to autofocus.")

        if microscope.has_real_stage():
            logging.debug("Running autofocus...")
            # Acquire microscope lock with 1s timeout
            with microscope.lock(timeout=1):
                # Run fast_autofocus
                return self.extension.fast_autofocus(microscope, dz=args.get("dz"))

        else:
            abort(503, "No stage connected. Unable to autofocus.")


class UpDownUpAutofocusAPI(ActionView):
    """
    Run a fast up-down-up autofocus
    """

    args = {
        "dz": fields.Int(missing=2000, example=2000),
        "backlash": fields.Int(missing=25, minimum=0),
    }

    def post(self, args):
        microscope = find_component("org.openflexure.microscope")

        if not microscope:
            abort(503, "No microscope connected. Unable to autofocus.")

        # Figure out the parameters to use
        dz = args.get("dz")
        backlash = args.get("backlash")

        if microscope.has_real_stage():
            logging.debug("Running autofocus...")

            # Acquire microscope lock with 1s timeout
            with microscope.lock(timeout=1):
                # Run fast_up_down_up_autofocus
                return self.extension.fast_up_down_up_autofocus(
                    microscope, dz=dz, mini_backlash=backlash
                )

        else:
            abort(503, "No stage connected. Unable to autofocus.")
