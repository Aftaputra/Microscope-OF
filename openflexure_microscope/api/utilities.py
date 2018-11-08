def parse_payload(request):
    """Convert request to JSON. Will eventually handle error-checking."""
    # TODO: Handle invalid JSON payloads
    state = request.get_json()
    return state


def gen(camera):
    """Video streaming generator function."""
    while True:
        # the obtained frame is a jpeg
        frame = camera.get_frame()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
