from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
from dask_flood_mapper import flood
import hvplot.xarray  # noqa
import os
import panel as pn

template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "templates"))
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
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
    print("####### time range: ", time_range)
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
        img_path = img_path = os.path.join(app.static_folder, "flood_map.html")
        pn.panel(fd_plot).save(img_path, embed=True)
        if os.path.exists(img_path):
            print("############## Image saved successfully.")
        else:
            print("################ Failed to save the image.")

        return jsonify({"image_url": "static/flood_map.html"}), 200

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
