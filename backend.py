from flask import Flask, request, jsonify
import csv
from datetime import datetime
import os

app = Flask(__name__)
CSV_FILE = "sensor_data.csv"

# Create CSV file with headers if not exists
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "soil_moisture", "humidity", "temperature"])

@app.route("/store", methods=["POST"])
def store():
    data = request.json
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Append to CSV
    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, data["soil_moisture"], data["humidity"], data["temperature"]])

    print(f"Data saved: {data}")
    return jsonify({"status": "success", "data": data})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
