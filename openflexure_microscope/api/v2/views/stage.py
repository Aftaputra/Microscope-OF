from labthings import find_component, fields, schema
from labthings.views import PropertyView

import logging


class StageTypeProperty(PropertyView):
    """The type of the stage"""

    def get(self):
        """
        Get the stage geometry.
        """
        microscope = find_component("org.openflexure.microscope")
        return microscope.configuration['stage']['type']
    
    schema = fields.String(missing=None, example="SangaStage", description="The stage geometry [SangaStage, SangaDeltaStage]")
    
    def put(self,stage_type):
        """
        Set the stage geometry.
        """
        microscope = find_component("org.openflexure.microscope")
        microscope.set_stage(stage_type=stage_type)
        return microscope.configuration["stage"]["type"]

