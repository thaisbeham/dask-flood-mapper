from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
from dask_flood_mapper import flood
import hvplot.xarray  # noqa
import os
import panel as pn
from importlib.resources import files
from appdirs import user_cache_dir
from pathlib import Path


IMAGE_FILE = "flood_map.html"
IMAGE_PATH = files("dask_flood_mapper").joinpath(IMAGE_FILE)
USER_CACHE_DIR_ = Path(user_cache_dir("dask_flood_mapper"))
print("§§§§§§ USER_CACHE_DIR: ", USER_CACHE_DIR_)

def make_user_cache_path(user_cache_dir):
    return user_cache_dir / IMAGE_FILE

if not USER_CACHE_DIR_.exists():
    USER_CACHE_DIR_.mkdir(parents=True)
user_cache_path = make_user_cache_path(USER_CACHE_DIR_)
print("§§§§§§§§ user cache path:", user_cache_path)

BASE_DIR = Path(__file__).parent  # folder where your script lives
template_dir = BASE_DIR / "templates"
#template_dir = "templates"
static_dir = USER_CACHE_DIR_
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
CORS(app)  



@app.route("/")
def index():
    return render_template("index.html")


@app.route("/check_flood", methods=["POST"])
def check_flood_status():
    data = request.json
    bbox = data.get("bbox")
    time_range = data.get("time_range")

    if not bbox or len(bbox) != 4:
        return jsonify({"error": "Invalid bounding box"}), 400
    if not time_range:
        return jsonify({"error": "Invalid time range"}), 400
    print("####### time range: ", time_range)
    print("user cache dir: ", user_cache_dir)
    try:
        # Call flood detection function
        fd = flood.decision(bbox=bbox, datetime=time_range).compute()
        print("################### calculation done")

        fd_plot = fd.hvplot.image(
            x="x",
            y="y",
            rasterize=True,
            geo=True,
            tiles=True,
            project=True,
            cmap=["rgba(0, 0, 1, 0.1)", "darkred"],
            cticks=[(0, "non-flood"), (1, "flood")],
            frame_width=600,
            frame_height=400,
        )
        print("############### plot done")
        img_path = user_cache_path 
        pn.panel(fd_plot).save(img_path, embed=True)

        if os.path.exists(img_path):
            print("############## Image saved successfully.")
        else:
            print("################ Failed to save the image.")

        return jsonify({"image_url": "/cache/flood_map.html"}), 200

    except Exception as e:
        print(f"############## Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/cache/<path:filename>")
def serve_cache_file(filename):
   return send_from_directory(
      USER_CACHE_DIR_, filename
   )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
