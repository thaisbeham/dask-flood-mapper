from flask import Flask, request, jsonify
from flask_cors import CORS
from dask_flood_mapper import flood  # Import your flood package
from dask_flood_mapper.processing import wcover
from dask.distributed import Client

app = Flask(__name__)
CORS(app)  # Allow frontend requests


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
        print("calculation done")
        fd_masked = fd.where(wcover != 80)

        fd_plot = fd_masked.hvplot.image(
            x="x",
            y="y",
            rasterize=True,
            geo=True,
            tiles=True,
            project=True,
            cmap=["rgba(0, 0, 1, 0.1)", "darkred"],
            cticks=[(0, "non-flood"), (1, "flood")],
            frame_height=400,
        )
        # result = fd.tolist()  # Convert to list if needed
        return jsonify({"matrix": fd_plot})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
