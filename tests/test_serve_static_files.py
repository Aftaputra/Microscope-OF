"""Test the code that mounts static files to the server, without creating a server."""

import os
import shutil
import tempfile

import pytest
from starlette.responses import FileResponse

from openflexure_microscope_server.server import serve_static_files


@pytest.fixture
def mock_app(mocker):
    """Return a mock FastAPI app.

    This is just a mock, where the get method returns a mock.
    """
    wrapper = mocker.Mock()
    app = mocker.Mock()
    app.get.return_value = wrapper
    return app


@pytest.fixture
def mock_static_dir():
    """Return the path of a mock static directory.

    It contains enough files to be recognised as a webapp.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, "js"))
        os.makedirs(os.path.join(tmpdir, "css"))
        with open(os.path.join(tmpdir, "index.html"), "w", encoding="utf-8") as f_obj:
            f_obj.write("<mock>mock</mock>")
        yield tmpdir


@pytest.mark.parametrize(
    "filename, allow_cache",
    [
        ["foo", False],
        ["woff2.foo", False],
        ["strange_file_ending_in_woff2", False],
        ["fontfile.woff2", True],
    ],
)
def test_add_static_file(filename, allow_cache, mock_app):
    """Test running add_static_file with both font and non-font files.

    This should creates a wrapped function that returns a FileResponse, this
    should be have the path on disk and the no cache headers if not a woff2 font.
    """
    wrapper = mock_app.get.return_value
    serve_static_files.add_static_file(mock_app, fname=filename, folder="bar")

    # It is called once
    assert mock_app.get.call_count == 1
    # Check args for the get decorator
    assert len(mock_app.get.call_args.args) == 1
    assert mock_app.get.call_args.args[0] == "/" + filename
    assert len(mock_app.get.call_args.kwargs) == 2
    assert mock_app.get.call_args.kwargs["response_class"] == FileResponse
    assert not mock_app.get.call_args.kwargs["include_in_schema"]

    # Checked wrapper and the the returned wrapped function
    assert wrapper.call_count == 1
    wrapped = wrapper.call_args.args[0]
    # the wrapped function should return the file response
    response = wrapped()
    assert isinstance(response, FileResponse)
    assert response.path == "bar/" + filename
    # The file response headers always have some standard data, and if the file is
    # allowed to be cached it should also have the no_cache data
    for key, value in serve_static_files.NO_CACHE_HEADERS.items():
        if allow_cache:
            assert key not in response.headers
        else:
            # Check headers that refuse caching are present
            assert key in response.headers
            assert response.headers[key] == value


def test_add_static_with_no_static_dir(mock_app, mocker):
    """Test that a FileNotFound error is raised if the static dir does not exist."""
    # Mock STATIC_PATH to something that doesn't exist
    mocker.patch(
        "openflexure_microscope_server.server.serve_static_files.STATIC_PATH",
        "fakepath",
    )
    # Should raise as the mock static dir does not exist
    with pytest.raises(FileNotFoundError):
        serve_static_files.add_static_files(mock_app, scans_folder=None)
    assert mock_app.get.call_count == 0


def test_check_static_dir(mocker, mock_static_dir):
    """Test check_static_dir recognises a basic webapp structure."""
    mocker.patch(
        "openflexure_microscope_server.server.serve_static_files.STATIC_PATH",
        mock_static_dir,
    )
    # First run shouldn't error as the mock dir has enough files.
    serve_static_files.check_static_dir()

    js_path = os.path.join(mock_static_dir, "js")
    index_path = os.path.join(mock_static_dir, "index.html")

    # Remove javascript dir and check error.
    shutil.rmtree(js_path)
    with pytest.raises(FileNotFoundError):
        serve_static_files.check_static_dir()
    # replace javascript dir with file, it should still error.
    shutil.copyfile(index_path, js_path)
    with pytest.raises(FileNotFoundError):
        serve_static_files.check_static_dir()

    # Return it to a folder and check everything works again
    os.remove(js_path)
    os.makedirs(js_path)
    serve_static_files.check_static_dir()

    # But it errors again if index.html is removed.
    os.remove(index_path)
    with pytest.raises(FileNotFoundError):
        serve_static_files.check_static_dir()
