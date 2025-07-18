import numpy as np
import logging
import cv2
import json
from PIL import Image
import time
from typing import Annotated, Any, Callable, Dict, List, Mapping, NamedTuple, Optional, Sequence, Tuple
from scipy.optimize import curve_fit
from camera_stage_mapping import camera_stage_tracker
from camera_stage_mapping import fft_image_tracking
from dataclasses import dataclass, field

from labthings_fastapi.thing import Thing
from labthings_fastapi.dependencies.thing import direct_thing_client_dependency
from labthings_fastapi.dependencies.invocation import CancelHook, InvocationLogger, InvocationCancelledError
from labthings_fastapi.decorators import thing_action, thing_property
from .stage import StageDependency as StageDep
from labthings_sangaboard import SangaboardThing
from labthings_picamera2.thing import StreamingPiCamera2
from labthings_fastapi.types.numpy import NDArray, denumpify, DenumpifyingDict
from openflexure_microscope_server.things.autofocus import AutofocusThing
from openflexure_microscope_server.things.camera_stage_mapping import CameraStageMapper

StageDep = direct_thing_client_dependency(SangaboardThing, "/stage/")
CamDep = direct_thing_client_dependency(StreamingPiCamera2, "/camera/")
CSMDep = direct_thing_client_dependency(CameraStageMapper, "/camera_stage_mapping/")
AutofocusDep = direct_thing_client_dependency(AutofocusThing, "/autofocus/")

def quadratic(x, a, b, c):
    '''
    Quadratic function
    '''  
    return a * x**2 + b * x + c

def dict_generate(dict_steps, stream_resolution, dir, factor = 1):
    '''
    Creates a single dictionary of step sizes 
    '''
    dict = {
        'x':(dict_steps/100) * stream_resolution[0] * factor * dir,
        'y':(dict_steps/100) * stream_resolution[1] * factor * dir
    }
    return dict

def steps_generate(small_step, z_perc, big_step, dir, stream_resolution):
    '''
    Creates all required dictionaries of all necessary step sizes. 
    '''
    step_sizes_big = dict_generate(big_step, stream_resolution, dir)
    step_sizes_small = dict_generate(small_step, stream_resolution, dir)
    minimum_offset_small = dict_generate(small_step, stream_resolution, dir, factor = 0.8)
    z_steps = dict_generate(z_perc, stream_resolution, dir)
    minimum_offset_z = dict_generate(z_perc, stream_resolution, dir, factor = 0.8)
    wrong_axis_max_small = dict_generate(small_step, stream_resolution, dir, factor = 0.1)
    wrong_axis_max_z = dict_generate(z_perc, stream_resolution, dir, factor = 0.1)

    return step_sizes_small, minimum_offset_small, z_steps, minimum_offset_z, step_sizes_big, wrong_axis_max_small, wrong_axis_max_z

class RangeofMotionThing(Thing):
    def rom_axis(
        self,
        autofocus: AutofocusDep,
        stage: StageDep,
        cam: CamDep,
        csm: CSMDep,
        cancel: CancelHook,
        logger: InvocationLogger,
        axis: str,
        direction: int
    ):
        """
        Measure the range of motion in a single axis and direction.
        """

        try:
            if direction == 1:
                dir_word = "positive"
            else:
                dir_word = "negative"
            
            logger.info(f"Beginning the {axis}-axis in the {dir_word} direction")

            stage_coords = []
            cor_lat_steps = []
            focused_positions = []
            axis_results = {}

            # Generate required dictionaries for step sizes and minimum offsets
            stream_resolution = cam.stream_resolution

            res_dic = {
                'x': stream_resolution[0],
                'y': stream_resolution[1]
            }

            step_sizes_small, minimum_offset_small, z_steps, minimum_offset_z, step_sizes_big, wrong_axis_max_small, wrong_axis_max_z = steps_generate(20, 50, 200, direction, stream_resolution=stream_resolution)

            delta = {
                'x':0,
                'y':0
            }

            logger.info(f"Using the follwing steps: {step_sizes_small, minimum_offset_small, z_steps, minimum_offset_z, step_sizes_big}")

            focus_data = autofocus.looping_autofocus(dz = 1000)

            starting_position = list(stage.position.values())

            parasitic_motion = False

            stage_coords.append(stage.position)

            logger.info("Moving the stage in 4 medium sized steps.")
            
            # Medium sized steps
            for loop in range(4):
                image1 = cv2.resize(np.array(Image.open(cam.grab_jpeg().open())), dsize=(0,0), fx= 1, fy= 1)
                if axis == 'x':
                    csm.move_in_image_coordinates(x = z_steps['x'], y = 0)
                    wrong_axis = 'y'
                else:
                    csm.move_in_image_coordinates(x = 0, y = z_steps['y'])
                    wrong_axis = 'x'
                focus_data = autofocus.looping_autofocus(dz = 800)
                image2 = cv2.resize(np.array(Image.open(cam.grab_jpeg().open())), dsize=(0,0), fx= 1, fy= 1)
                offset = [x * 1 for x in fft_image_tracking.displacement_between_images(image_0 = image1, image_1 = image2, sigma=10, fractional_threshold=0.1, pad=True)] # Units is pixels
                delta['x'] = int(offset[1])
                delta['y'] = int(offset[0])
                logger.info(f"Offset measured as {delta[axis]}")
                stage_coords.append(stage.position)
                cor_lat_steps.append(offset)
                focused_positions.append(stage.position)

                # Check for parasitic motion

                if np.abs(delta[wrong_axis]) > np.abs(wrong_axis_max_z[wrong_axis]):
                    logger.info(f"Parasitic motion detected in {wrong_axis}-axis whilst measuring {axis}-axis.")
                    parasitic_motion = True
                    break

            pixel_per_step = ((1/abs(csm.image_to_stage_displacement_matrix[0][1])) 
                            + (1/abs(csm.image_to_stage_displacement_matrix[1][0])))/4
            lateral_positions = [i[axis] for i in focused_positions]
            z_positions = [i['z'] for i in focused_positions]
            parameters, covariance = curve_fit(quadratic, lateral_positions, z_positions)
            relative_move = direction * 2 * res_dic[axis]/(2*pixel_per_step) # This is the number of steps to cover 200% of the FOV.
            z_dest = quadratic(stage.position[axis] + relative_move, *parameters)
            z_diff = z_dest - stage.position['z']

            logger.info(f"Z calibration complete.")

            # 1 big step followed by 3 small steps
            while np.abs(delta[axis]) > np.abs(minimum_offset_small[axis]) and parasitic_motion == False:

                stage.move_relative(z = z_diff)

                logger.info(f"Moved in z by {z_diff}") 

                if axis == 'x':
                    csm.move_in_image_coordinates(x = step_sizes_big['x'], y = 0)
                else:
                    csm.move_in_image_coordinates(x = 0, y = step_sizes_big['y'])

                stage_coords.append(stage.position)

                failure_count = 0

                for loop in range(3):
                    image1 = cv2.resize(np.array(Image.open(cam.grab_jpeg().open())), dsize=(0,0), fx= 1, fy= 1)
                    if axis == 'x':
                        csm.move_in_image_coordinates(x = step_sizes_small['x'], y = 0)
                    else:
                        csm.move_in_image_coordinates(x = 0, y = step_sizes_small['y'])
                    focus_data = autofocus.looping_autofocus(dz = 800)
                    image2 = cv2.resize(np.array(Image.open(cam.grab_jpeg().open())), dsize=(0,0), fx= 1, fy= 1)
                    offset = [x * 1 for x in fft_image_tracking.displacement_between_images(image_0 = image1, image_1 = image2, sigma=10, fractional_threshold=0.1, pad=True)] # Units is pixels
                    delta['x'] = int(offset[1])
                    delta['y'] = int(offset[0])
                    logger.info(f"Offset measured as {delta[axis]}")
                    
                    while np.abs(delta[axis]) < minimum_offset_small[axis] and failure_count < 3:
                        logger.info(f"Correlation failed. Refocusing to check. Attempt {failure_count + 1}/3")
                        focus_data = autofocus.looping_autofocus(dz = 1000)
                        image2 = cv2.resize(np.array(Image.open(cam.grab_jpeg().open())), dsize=(0,0), fx= 1, fy= 1)           
                        failure_count += 1
                        offset = [x * 1 for x in fft_image_tracking.displacement_between_images(
                            image_0 = image1, image_1 = image2, sigma=10, fractional_threshold=0.1, pad=True)] # Units is pixels
                        delta['x'] = int(offset[1])
                        delta['y'] = int(offset[0])
                        logger.info(f"Displacement found was {np.abs(delta[axis])}. Minimum offset is {minimum_offset_small[axis]}")

                    stage_coords.append(stage.position)
                    cor_lat_steps.append(offset)
                    focused_positions.append(stage.position)

                    if np.abs(delta[wrong_axis]) > np.abs(wrong_axis_max_small[wrong_axis]):
                        logger.info(f"Parasitic motion detected in {wrong_axis}-axis whilst measuring {axis}-axis.")
                        parasitic_motion = True
                        break

                    if np.abs(delta[axis]) < np.abs(minimum_offset_small[axis]):  # this means the edge has been found
                        logger.info(f"Edge has been found.")
                        break

            # Motion detection

            logger.info(f"Running motion detection")

            displacements = np.array([1,2,4,8,16,32,64,128,256,512,1024])  # Array of increasing step sizes
            motion_minimum = 20  # minimum nuber of pixels for motion to be detected

            this_motion_step = {
                'x':np.zeros(np.shape(displacements)[0]),
                'y':np.zeros(np.shape(displacements)[0]),
                'z':0
            }

            this_motion_step[axis] = displacements * direction * -1
            
            for loop in range(np.shape(displacements)[0]):
                logger.info(f"Testing with step size {this_motion_step[axis][loop]}")
                image1 = cv2.resize(np.array(Image.open(cam.grab_jpeg().open())), dsize=(0,0), fx= 1, fy= 1)           
                stage.move_relative(x = this_motion_step['x'][loop], y = this_motion_step['y'][loop], z = this_motion_step['z'])
                image2 = cv2.resize(np.array(Image.open(cam.grab_jpeg().open())), dsize=(0,0), fx= 1, fy= 1)           
                offset = [x * 1 for x in fft_image_tracking.displacement_between_images(
                    image_0 = image1, image_1 = image2, sigma=10, fractional_threshold=0.1, pad=True)] # Units is pixels
                delta['x'] = int(offset[1])
                delta['y'] = int(offset[0])
                logger.info(f"Offset measured as {np.abs(delta[axis])}")
                if np.abs(delta[axis]) > motion_minimum:
                    logger.info("Motion detected.")
                    break

            stage_coords[np.shape(stage_coords)[0] - 1] = stage.position

            final_pos = stage.position

            axis_results = {
                "correlation_lateral_steps": cor_lat_steps,
                "stage_positions": stage_coords,
                "final_position": final_pos
            }

            stage.move_absolute(x = starting_position[0], y = starting_position[1], z = starting_position[2], block_cancellation=True)



        except:
            logger.error("Stopping measurement because it was cancelled by the user")
            stage.move_absolute(x = starting_position[0], y = starting_position[1], z = starting_position[2], block_cancellation=True)
            raise Exception
        return axis_results

    @thing_action
    def rom_main(
        self,
        autofocus: AutofocusDep,
        stage: StageDep,
        cam: CamDep,
        csm: CSMDep,
        cancel: CancelHook,
        logger: InvocationLogger
    ):
        """
        Measures the range of motion of the stage across the x and y axes.
        """
        logger.info("Using the stage to measure the Range of Motion. Please ensure you are using a big enough sample.")
        x_pos_results = self.rom_axis( 
            autofocus,
            stage,
            cam,
            csm,
            cancel,
            logger,
            axis = 'x', 
            direction = 1
        )
        # for axis_dir in [['x', 1],['x', -1],['y', 1],['y', -1]]:
        #     axis_dir_results = self.rom_axis(
        #         autofocus,
        #         stage,
        #         cam,
        #         csm,
        #         cancel,
        #         logger,
        #         axis = axis_dir[0], 
        #         direction = axis_dir[1]
        #         )
        return x_pos_results
    
           
