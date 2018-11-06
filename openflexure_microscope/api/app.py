#!/usr/bin/env python
#TODO: Completely rewrite for new version of StreamingCamera
from pprint import pprint
from importlib import import_module
import time, datetime

from flask import Flask, render_template, Response, redirect, request, jsonify, send_file
#import yaml
import numpy as np

# Raspberry Pi camera module (requires picamera package)
#from camera.pi import Camera
from openflexure_microscope.camera.pi import StreamingCamera

app = Flask(__name__)
cam = StreamingCamera()

def parse_payload(request):
    # TODO: Try-except for invalid JSON payloads
    state = request.get_json()
    return state

def gen(camera):
    """Video streaming generator function."""
    while True:
        # the obtained frame is a jpeg
        frame = camera.get_frame()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    '''
    Video streaming home page.
    '''
    cam.start_worker()  # Start the stream
    return render_template('index.html')

@app.route('/stream')
def stream():
    '''
    Video streaming route. Put this in the src attribute of an img tag.
    '''
    return Response(gen(cam), mimetype='multipart/x-mixed-replace; boundary=frame')


#TODO: Be able to change the image resolution with an option
@app.route('/capture/', methods=['GET', 'POST', 'PUT'])
def capture():
    '''
    POST/PUT: Capture a single image
    GET: Return capture status, or download latest capture

    Eg. curl http://192.168.1.140:5000/capture/ -H "Content-Type: application/json" -d '{"store":true}' -X POST
    '''
    if request.method == 'POST' or request.method == 'PUT':
        state = parse_payload(request)
        print(state)

        # Handle filename argument
        if 'filename' in state:
            filename = state['filename']
        else:
            filename = None
        
        if 'write_to_file' in state:
            write_to_file = bool(state['write_to_file'])
        else:
            write_to_file = False

        if 'use_video_port' in state:
            use_video_port = bool(state['use_video_port'])
        else:
            use_video_port = False
        
        if 'resize' in state:
            resize_h = int(state['resize'])
            resize_w = int(resize_h*(4/3))
            resize = (resize_w, resize_h)
        else:
            resize = None

        response = cam.capture(
            write_to_file=write_to_file, 
            use_video_port=use_video_port,
            filename=filename,
            resize=resize)

        return str(response) + "\n"

    else:  # If GET request

        download = request.args.get('download')

        state = cam.state
        
        if (download == 'true' or download == 'True' or download =='1') and cam.image is not None:
            return send_file(cam.image.data, mimetype='image/jpeg')
        else:
            return jsonify(state)

@app.route('/record/', methods=['GET', 'POST', 'PUT'])
def record():
    '''
    POST/PUT: Start or stop a video recording
    GET: Return recording status, or download latest recording

    Eg. 
    curl http://192.168.1.140:5000/record/ -H "Content-Type: application/json" -d '{"status":true}' -X POST
    curl http://192.168.1.140:5000/record/ -H "Content-Type: application/json" -d '{"status":false}' -X POST
    '''
    if request.method == 'POST' or request.method == 'PUT':
        state = request.get_json()
        print(state)

        # Handle filename argument
        if 'filename' in state:
            filename = state['filename']
        else:
            filename = None

        # Handle status argument
        if 'status' in state:
            status = bool(state['status'])

        # synchronise the arduino_time
        if status == True:
            response = cam.start_recording(filename=filename)
            return str(response)

        elif status == False:
            response = cam.stop_recording()
            return str(response)
    
    else:
        download = request.args.get('download')

        state = cam.state
        
        if (download == 'true' or download == 'True' or download =='1') and cam.state_record['recent'] is not None:
            return send_file(cam.state_record['recent'],
                mimetype='video/H264',
                as_attachment=True)
        else:
            return jsonify(state)

@app.route('/preview/', methods=['GET', 'POST', 'PUT'])
def preview():
    '''
    POST/PUT: Start or stop the direct-to-GPU camera preview on the Pi
    GET: Return preview status
    '''
    if request.method == 'POST' or request.method == 'PUT':
        state = request.get_json()
        print(state)

        if 'status' in state:
            status = bool(state['status'])

        if status == False:
            response = cam.stop_preview()
        else:
            response = cam.start_preview()

        return str(response)
    
    else:
        # Get args passed via URL (not useful here. Just for reference.)
        state = cam.state
        return jsonify(state)


if __name__ == '__main__':
    app.run(host='0.0.0.0', threaded=True, debug=True, use_reloader=False)