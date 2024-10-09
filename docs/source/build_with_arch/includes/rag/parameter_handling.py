from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route("/agent/device_summary", methods=["POST"])
def get_device_summary():
    """
    Endpoint to retrieve device statistics based on device IDs and an optional time range.
    """
    data = request.get_json()

    # Validate 'device_ids' parameter
    device_ids = data.get("device_ids")
    if not device_ids or not isinstance(device_ids, list):
        return (
            jsonify({"error": "'device_ids' parameter is required and must be a list"}),
            400,
        )

    # Validate 'time_range' parameter (optional, defaults to 7)
    time_range = data.get("time_range", 7)
    if not isinstance(time_range, int):
        return jsonify({"error": "'time_range' must be an integer"}), 400

    # Simulate retrieving statistics for the given device IDs and time range
    # In a real application, you would query your database or external service here
    statistics = []
    for device_id in device_ids:
        # Placeholder for actual data retrieval
        stats = {
            "device_id": device_id,
            "time_range": f"Last {time_range} days",
            "data": f"Statistics data for device {device_id} over the last {time_range} days.",
        }
        statistics.append(stats)

    response = {"statistics": statistics}

    return jsonify(response), 200


if __name__ == "__main__":
    app.run(debug=True)
