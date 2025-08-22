"""Provide fixtures that can be reused by the entire test suite.

For more information on this pattern see:
https://docs.pytest.org/en/stable/reference/fixtures.html#conftest-py-sharing-fixtures-across-multiple-files
"""

import pytest


@pytest.fixture
def mock_app(mocker):
    """Return a mock FastAPI app.

    This is just a mock, where the get method returns a mock.
    """
    wrapper = mocker.Mock()
    app = mocker.Mock()
    app.get.return_value = wrapper
    return app
