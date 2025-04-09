import webbrowser
import threading
from dask_flood_mapper.app import app


def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000")


def main():
    threading.Timer(1.5, open_browser).start()
    app.run()
