"""Test the code that mounts static files to the server, without creating a server."""

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
