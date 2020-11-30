import os
import threading
import time

from openflexure_microscope.camera.base import FrameStream


def test_framestream_write():
    d = b"openflexure"

    with FrameStream() as f:
        f.write(d)
        assert f.getvalue() == d


def test_framestream_overwrite():
    d1 = b"openflexure"
    d2 = b"microscope"

    with FrameStream() as f:
        f.write(d1)
        assert f.getvalue() == d1
        f.write(d2)
        assert f.getvalue() == d2
        # d1 should be removed, so f.getbuffer() should only contain d2
        assert f.getbuffer().nbytes == len(d2)


def test_tracker():
    sizes = range(1, 100)

    with FrameStream() as f:
        for length in sizes:
            time.sleep(0.01)
            d = b"\x00" + os.urandom(length) + b"\x00"
            f.write(d)
            assert f.getbuffer().nbytes == len(d)

        # Make sure we have one TrackerFrame for each f.write() call
        assert len(f.frames) == len(sizes)
        # For each tested write size
        for i, frame in enumerate(f.frames):
            # Make sure the recorded size is what we expect
            # Should be size +2 for our padding bytes \x00
            assert frame.size == sizes[i] + 2
            # Make sure we have a valid time value
            assert isinstance(frame.time, float)
            # Make sure the recorded time increases for each frame
            if i > 0:
                assert f.frames[i].time > f.frames[i - 1].time

        # Test FrameStream.last
        assert f.last.size == sizes[-1] + 2


def test_new_frame_event():
    d = b"openflexure"

    def target(framestream):
        time.sleep(0.01)
        framestream.write(d)

    with FrameStream() as f:
        # Start a thread to write some data
        thread = threading.Thread(target=target, args=(f,))
        thread.daemon = True
        thread.start()
        # Make sure the stream is empty before we wait for a frame
        assert not f.getvalue()
        # Wait for a frame to be written
        frame = f.getframe()
        assert frame == d
        # Make sure getframe() cleared the event
        assert not f.new_frame.events[threading.get_ident()][0].is_set()
