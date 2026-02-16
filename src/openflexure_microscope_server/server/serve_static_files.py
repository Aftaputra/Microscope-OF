"""Add endpoints for static files to the underlying FastAPI server."""

import os
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_PATH = os.path.normpath(os.path.join(THIS_DIR, "..", "static"))

NO_CACHE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}


def add_static_file(app: FastAPI, fname: str, folder: str) -> None:
    """Add a single file to the root of the FastAPI app.

    The file  with name ``fname`` will be mounted at ``/fname`` - the
    ``folder`` does not affect where it is mounted in the app.

    app: The FastAPI app to add to, in this case the OpenFlexure server
    fname: the name of the file to add
    folder: the containing folder of the file
    """
    file_path = os.path.join(folder, fname)
    # Cache font files, but not other static files in the root static directory.
    headers = {} if fname.endswith(".woff2") else NO_CACHE_HEADERS

    app.get(f"/{fname}", response_class=FileResponse, include_in_schema=False)(
        lambda: FileResponse(file_path, headers=headers)
    )


def add_static_files(app: FastAPI, scans_folder: Optional[str]) -> None:
    """Add the static files responsible for the webapp app to the FastAPI app.

    Note that any file in the root of the static dir will not be cached. However, the
    files in mounted subdirectories are not sent with no-cache headers.
    The Vue CSS and JS are hashed, so if updated their filename will update. The most
    important file not to cache is "index.html".

    :param app: The FastAPI app to add to, in this case the OpenFlexure server
    :param scans_folder: The directory for the scans.
    """
    check_static_dir()

    @app.get("/", response_class=RedirectResponse)
    async def redirect_fastapi() -> str:
        return "/index.html"

    # Mounting the webapp at / file by file to allow other endpoints to be created
    for fname in os.listdir(STATIC_PATH):
        fpath = os.path.join(STATIC_PATH, fname)
        if os.path.isfile(fpath):
            add_static_file(app, fname, STATIC_PATH)
        elif os.path.isdir(fpath):
            app.mount(
                f"/{fname}/",
                StaticFiles(directory=fpath),
                name=f"static_{fname}",
            )

    # If scans folder is None, there is not smart scan thing. So nothing to mount.
    if scans_folder is not None:
        # Mount the scan directory to .../scans/, to allow dzi viewing
        if not os.path.isdir(scans_folder):
            os.makedirs(scans_folder)
        app.mount(
            "/scans/",
            StaticFiles(directory=scans_folder),
            name="scans",
        )


def check_static_dir() -> None:
    """Check that the static dir exists and contains expected files and dirs."""
    if not os.path.isdir(STATIC_PATH):
        raise FileNotFoundError(
            "The static directory does not exist. You will need to pull or compile the"
            "web app."
        )
    expected = [
        os.path.isdir(os.path.join(STATIC_PATH, "assets")),
        os.path.isfile(os.path.join(STATIC_PATH, "index.html")),
    ]
    if not all(expected):
        raise FileNotFoundError(
            "The static directory does not contain a valid web app. You will need to "
            "pull or compile the web app."
        )
