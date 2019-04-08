from openflexure_microscope.api.v1.views import MicroscopeViewPlugin
from openflexure_microscope.api.utilities import JsonPayload

from flask import request, jsonify, abort


class TileScanAPI(MicroscopeViewPlugin):
    def post(self):
        payload = JsonPayload(request)

        # Get params
        filename = payload.param('filename')

        step_size = payload.param('step_size', default=[2000, 1500, 100], convert=list)
        step_size = [int(i) for i in step_size]

        grid = payload.param('grid', default=[3, 3, 5], convert=list)
        grid = [int(i) for i in grid]

        style = payload.param('style', default='raster', convert=str)
        autofocus_dz = payload.param('autofocus_dz', default=50, convert=int)

        use_video_port = payload.param('use_video_port', default=True, convert=bool)
        resize = payload.param('size', default=None)
        if resize:
            if ('width' in resize) and ('height' in resize):
                resize = (int(resize['width']), int(resize['height']))  # Convert dict to tuple
            else:
                abort(404)

        bayer = payload.param('bayer', default=False, convert=bool)
        metadata = payload.param('metadata', default={}, convert=dict)
        tags = payload.param('tags', default=[], convert=list)

        print("Running tile scan...")
        task = self.microscope.task.start(
            self.plugin.tile,
            basename=filename,
            step_size=step_size,
            grid=grid,
            style=style,
            autofocus_dz=autofocus_dz,
            use_video_port=use_video_port,
            resize=resize,
            bayer=bayer,
            metadata=metadata,
            tags=tags
        )

        # return a handle on the autofocus task
        return jsonify(task.state), 202


class ZStackAPI(MicroscopeViewPlugin):
    def post(self):
        payload = JsonPayload(request)

        # Get params
        name = payload.param('name')
        step_size = payload.param('step_size', default=100, convert=int)
        steps = payload.param('steps', default=5, convert=int)
        center = payload.param('center', default=True, convert=bool)

        use_video_port = payload.param('use_video_port', default=False, convert=bool)
        resize = payload.param('size', default=None)
        if resize:
            if ('width' in resize) and ('height' in resize):
                resize = (int(resize['width']), int(resize['height']))  # Convert dict to tuple
            else:
                abort(404)

        bayer = payload.param('bayer', default=True, convert=bool)
        metadata = payload.param('metadata', default={}, convert=dict)
        tags = payload.param('tags', default=[], convert=list)

        print("Running tile scan...")
        task = self.microscope.task.start(
            self.plugin.stack,
            basename=name,
            step_size=step_size,
            steps=steps,
            center=center,
            use_video_port=use_video_port,
            resize=resize,
            bayer=bayer,
            metadata=metadata,
            tags=tags
        )

        # return a handle on the autofocus task
        return jsonify(task.state), 202
