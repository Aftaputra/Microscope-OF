import shutil
from typing import Mapping, Optional
import cv2
from fastapi import HTTPException
from fastapi.responses import FileResponse
import numpy as np
import os
import time
from PIL import Image
from pydantic import BaseModel
from scipy.stats import norm
import logging
from copy import deepcopy
from datetime import datetime
from subprocess import CompletedProcess, run, PIPE

from labthings_fastapi.thing import Thing
from labthings_fastapi.dependencies.raw_thing import raw_thing_dependency
from labthings_fastapi.dependencies.invocation import CancelHook, InvocationLogger, InvocationCancelledError
from labthings_fastapi.decorators import thing_action
from labthings_fastapi.outputs.blob import BlobOutput
from openflexure_microscope_server.things.autofocus import AutofocusThing
from openflexure_microscope_server.things.camera_stage_mapping import CameraStageMapper
from openflexure_microscope_server.things.auto_recentre_stage import RecentringThing

from .smart_scan import SmartScanThing

SmartScanDep = raw_thing_dependency(SmartScanThing)


class JPEGBlob(BlobOutput):
    media_type = "image/jpeg"


class Stitcher(Thing):
    def __init__(self, path_to_openflexure_stitch: str):
        self._script = path_to_openflexure_stitch

    def run_subprocess(
            self, logger: InvocationLogger, cmd: list[str],
        ) -> CompletedProcess:
        """Run a  subprocess and log any output"""
        logger.info(f"Running command in subprocess: `{' '.join(cmd)}")
        output = run(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True)
        for pipe in [output.stdout, output.stderr]:
            if pipe:
                logger.info(pipe)
        output.check_returncode()
        return output
    
    def images_folder(self, smart_scan: SmartScanDep, scan_name: Optional[str]=None) -> str:
        scan_folder = smart_scan.scan_folder_path(scan_name=scan_name)
        return os.path.join(scan_folder, "images")

    @thing_action
    def stitch_scan_from_stage(self, logger: InvocationLogger, smart_scan: SmartScanDep, scan_name: Optional[str]=None, downsample: float=1.0) -> JPEGBlob:
        """Generate a stitched image based on stage position metadata"""
        images_folder = self.images_folder(smart_scan=smart_scan, scan_name=scan_name)
        self.run_subprocess(logger, [self._script, "--stitching_mode", "only_stage_stitch", images_folder])
        return JPEGBlob.from_file(os.path.join(images_folder, "stitched_from_stage.jpg"))
    
    @thing_action
    def update_scan_correlations(self, logger: InvocationLogger, smart_scan: SmartScanDep, scan_name: Optional[str]=None) -> None:
        """Generate a stitched image based on stage position metadata"""
        images_folder = self.images_folder(smart_scan=smart_scan, scan_name=scan_name)
        self.run_subprocess(logger, [self._script, "--stitching_mode", "only_correlate", images_folder])

    @thing_action
    def stitch_scan(self, logger: InvocationLogger, smart_scan: SmartScanDep, scan_name: Optional[str]=None, downsample: float=1.0) -> None:
        """Generate a stitched image based on stage position metadata"""
        images_folder = self.images_folder(smart_scan=smart_scan, scan_name=scan_name)
        self.run_subprocess(logger, [self._script, "--stitching_mode", "all", images_folder])
