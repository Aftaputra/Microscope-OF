from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI
import os

def add_static_file(app: FastAPI, fname: str, folder: str):
    print(f"Adding route for /{fname}")
    p=os.path.join(folder, fname)
    app.get(
        f"/{fname}",
        response_class=FileResponse,
        include_in_schema=False
    )(lambda: FileResponse(p))

def add_static_files(app: FastAPI):
    #with importlib.resources.as_file(openflexure_microscope_server) as p:
    #   static_path = p.join("/static/")
    static_path = "./src/openflexure_microscope_server/static"
    if not os.path.isdir(static_path):
        raise RuntimeError("Can't find static files :(")

    for folder in ["css", "js", "fonts"]:
        app.mount(
            f"/{folder}/",
            StaticFiles(directory=os.path.join(static_path, folder)),
            name=f"static_{folder}",
        )
    @app.get("/", response_class=RedirectResponse)
    async def redirect_fastapi():
        return "/index.html"
    for fname in os.listdir(static_path):
        add_static_file(app, fname, static_path)
