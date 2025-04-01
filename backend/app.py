from flask import Flask, request, jsonify
from flask import send_from_directory, render_template
from flask_cors import CORS
from dask_flood_mapper import flood
from dask.distributed import Client
import hvplot.xarray  # noqa
import holoviews as hv
import os
from selenium import webdriver
from webdriver_manager.firefox import GeckoDriverManager
import panel as pn

hv.extension("bokeh")

pn.extension("bokeh")

driver = webdriver.Firefox(
    service=webdriver.firefox.service.Service(GeckoDriverManager().install())
)

app = Flask(__name__)  # , static_folder="static", template_folder="../frontend")
CORS(app)  # Allow frontend requests


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

    try:
        # Call flood detection function
        client = Client(  # noqa
            processes=False, threads_per_worker=2, n_workers=1, memory_limit="12GB"
        )  # noqa
        fd = flood.decision(bbox=bbox, datetime=time_range).compute()
        print("################### calculation done")

        # data_text = files("dask_flood_mapper.data").joinpath("wcover.tif")
        # wcover = xr.open_dataarray(data_text, band_as_variable=True)
        # fd_masked = fd.where(wcover != 80)

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
        img_path = "static/flood_map.png"
        hv.save(fd_plot, img_path, fmt="png", dpi=100)
        if os.path.exists(img_path):
            print("############## Image saved successfully.")
        else:
            print("################ Failed to save the image.")

        # result = fd.tolist()  # Convert to list if needed
        return jsonify({"image_url": "static/flood_map.png"}), 200
        # return jsonify({"image_url": url_for('static', filename='flood_map.png', _external=True)}), 200
    except Exception as e:
        print(f"############## Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/static/<path:filename>")
def static_file(filename):
    return send_from_directory(
        os.path.join(os.path.dirname(__file__), "static"), filename
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
