def parse_payload(request):
    """Convert request to JSON. Will eventually handle error-checking."""
    # TODO: Handle invalid JSON payloads
    state = request.get_json()
    return state


def get_from_payload(payload, key, default=None):
    """Check if a key exists in a JSON/dictionary payload, and returns it."""
    if key in payload:
        return payload[key]
    else:
        return default


def gen(camera):
    """Video streaming generator function."""
    while True:
        # the obtained frame is a jpeg
        frame = camera.get_frame()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


def get_bool(get_arg):
    """Convert GET request argument string to a Python bool"""
    if (
        get_arg == 'true' or
        get_arg == 'True' or
        get_arg == '1'):
        return True
    else:
        return False