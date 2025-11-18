# ----------------------------------------------------------
# COM682 Coursework 2 – Multimedia GP Portal (Cloud-Native)
# Flask API for file upload & record management
# Author: Paul Johnston (B00888517)
# ----------------------------------------------------------

from flask import Flask, request, jsonify
from flask_cors import CORS
from services.storage import upload_bytes
from services.cosmos import upsert_record, list_records, get_record_by_id, update_record_by_id
import os, uuid, time, logging

# ----------------------------------------------------------
# Flask setup + CORS
# ----------------------------------------------------------
app = Flask(__name__)

# Allow all origins for now (local file://, localhost, future static web app)
CORS(app, resources={r"/*": {"origins": "*"}})

# Optional logging for debugging / later Application Insights
logging.basicConfig(level=logging.INFO)

# ----------------------------------------------------------
# Health check endpoint
# ----------------------------------------------------------
@app.get("/health")
def health():
    app.logger.info("Health check called")
    return jsonify(status="ok", service="gpportal-api"), 200


# ----------------------------------------------------------
# Upload endpoint (Patient Portal)
# ----------------------------------------------------------
@app.post("/upload")
def upload():
    # Validate file
    if "file" not in request.files:
        return jsonify(error="file missing"), 400

    file = request.files["file"]
    patient_id = (request.form.get("patientId") or "unknown").strip()

    if not patient_id:
        return jsonify(error="patientId required"), 400

    # Generate unique blob name: patientId/uuid.ext
    ext = (file.filename or "file").split(".")[-1].lower()
    blob_name = f"{patient_id}/{uuid.uuid4()}.{ext}"

    # Upload to Blob Storage
    try:
        url = upload_bytes(blob_name, file.read(), file.mimetype)
    except Exception as e:
        app.logger.error(f"Blob upload failed: {e}")
        return jsonify(error="upload failed"), 500

    # Create a Cosmos DB record
    record = {
        "id": str(uuid.uuid4()),
        "patientId": patient_id,
        "blobUrl": url,
        "originalName": file.filename,
        "contentType": file.mimetype,
        "status": "pending",   # Logic App / GP will enrich later
        "gpNotes": "",
        "createdAt": int(time.time())
    }

    try:
        upsert_record(record)
    except Exception as e:
        app.logger.error(f"Cosmos upsert failed: {e}")
        return jsonify(error="database error"), 500

    app.logger.info(f"File uploaded for patient {patient_id}")
    return jsonify(message="uploaded", blobUrl=url, record=record), 201


# ----------------------------------------------------------
# Retrieve patient records (Patient Portal + GP Dashboard)
# ----------------------------------------------------------
@app.get("/records")
def records():
    patient_id = request.args.get("patientId")
    if not patient_id:
        return jsonify(error="patientId query param required"), 400

    try:
        items = list_records(patient_id)
        return jsonify(records=items, count=len(items)), 200
    except Exception as e:
        app.logger.error(f"Error fetching records: {e}")
        return jsonify(error="failed to fetch records"), 500


# ----------------------------------------------------------
# Get a single record by id (GP Dashboard detail view)
# ----------------------------------------------------------
@app.get("/record/<record_id>")
def get_record(record_id):
    try:
        rec = get_record_by_id(record_id)
        if not rec:
            return jsonify(error="record not found"), 404
        return jsonify(rec), 200
    except Exception as e:
        app.logger.error(f"Error fetching record {record_id}: {e}")
        return jsonify(error="failed to fetch record"), 500


# ----------------------------------------------------------
# Update a record (GP review: status + notes)
# ----------------------------------------------------------
@app.put("/record/<record_id>")
def update_record(record_id):
    data = request.get_json() or {}

    updates = {}
    if "status" in data:
        updates["status"] = data["status"]
    if "gpNotes" in data:
        updates["gpNotes"] = data["gpNotes"]

    # Add audit timestamp
    updates["updatedAt"] = int(time.time())

    try:
        updated = update_record_by_id(record_id, updates)
        if not updated:
            return jsonify(error="record not found"), 404
        return jsonify(updated), 200
    except Exception as e:
        app.logger.error(f"Error updating record {record_id}: {e}")
        return jsonify(error="failed to update record"), 500


# ----------------------------------------------------------
# Entry point
# ----------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
# ----------------------------------------------------------
# COM682 Coursework 2 – Multimedia GP Portal (Cloud-Native)
# Flask API for file upload & record management
# Author: Paul Johnston (B00888517)
# ----------------------------------------------------------

from flask import Flask, request, jsonify
from flask_cors import CORS
from services.storage import upload_bytes
from services.cosmos import upsert_record, list_records, get_record_by_id, update_record_by_id
import os, uuid, time, logging

# ----------------------------------------------------------
# Flask setup + CORS
# ----------------------------------------------------------
app = Flask(__name__)

# Allow all origins for now (local file://, localhost, future static web app)
CORS(app, resources={r"/*": {"origins": "*"}})

# Optional logging for debugging / later Application Insights
logging.basicConfig(level=logging.INFO)

# ----------------------------------------------------------
# Health check endpoint
# ----------------------------------------------------------
@app.get("/health")
def health():
    app.logger.info("Health check called")
    return jsonify(status="ok", service="gpportal-api"), 200


# ----------------------------------------------------------
# Upload endpoint (Patient Portal)
# ----------------------------------------------------------
@app.post("/upload")
def upload():
    # Validate file
    if "file" not in request.files:
        return jsonify(error="file missing"), 400

    file = request.files["file"]
    patient_id = (request.form.get("patientId") or "unknown").strip()

    if not patient_id:
        return jsonify(error="patientId required"), 400

    # Generate unique blob name: patientId/uuid.ext
    ext = (file.filename or "file").split(".")[-1].lower()
    blob_name = f"{patient_id}/{uuid.uuid4()}.{ext}"

    # Upload to Blob Storage
    try:
        url = upload_bytes(blob_name, file.read(), file.mimetype)
    except Exception as e:
        app.logger.error(f"Blob upload failed: {e}")
        return jsonify(error="upload failed"), 500

    # Create a Cosmos DB record
    record = {
        "id": str(uuid.uuid4()),
        "patientId": patient_id,
        "blobUrl": url,
        "originalName": file.filename,
        "contentType": file.mimetype,
        "status": "pending",   # Logic App / GP will enrich later
        "gpNotes": "",
        "createdAt": int(time.time())
    }

    try:
        upsert_record(record)
    except Exception as e:
        app.logger.error(f"Cosmos upsert failed: {e}")
        return jsonify(error="database error"), 500

    app.logger.info(f"File uploaded for patient {patient_id}")
    return jsonify(message="uploaded", blobUrl=url, record=record), 201


# ----------------------------------------------------------
# Retrieve patient records (Patient Portal + GP Dashboard)
# ----------------------------------------------------------
@app.get("/records")
def records():
    patient_id = request.args.get("patientId")
    if not patient_id:
        return jsonify(error="patientId query param required"), 400

    try:
        items = list_records(patient_id)
        return jsonify(records=items, count=len(items)), 200
    except Exception as e:
        app.logger.error(f"Error fetching records: {e}")
        return jsonify(error="failed to fetch records"), 500


# ----------------------------------------------------------
# Get a single record by id (GP Dashboard detail view)
# ----------------------------------------------------------
@app.get("/record/<record_id>")
def get_record(record_id):
    try:
        rec = get_record_by_id(record_id)
        if not rec:
            return jsonify(error="record not found"), 404
        return jsonify(rec), 200
    except Exception as e:
        app.logger.error(f"Error fetching record {record_id}: {e}")
        return jsonify(error="failed to fetch record"), 500


# ----------------------------------------------------------
# Update a record (GP review: status + notes)
# ----------------------------------------------------------
@app.put("/record/<record_id>")
def update_record(record_id):
    data = request.get_json() or {}

    updates = {}
    if "status" in data:
        updates["status"] = data["status"]
    if "gpNotes" in data:
        updates["gpNotes"] = data["gpNotes"]

    # Add audit timestamp
    updates["updatedAt"] = int(time.time())

    try:
        updated = update_record_by_id(record_id, updates)
        if not updated:
            return jsonify(error="record not found"), 404
        return jsonify(updated), 200
    except Exception as e:
        app.logger.error(f"Error updating record {record_id}: {e}")
        return jsonify(error="failed to update record"), 500


# ----------------------------------------------------------
# Entry point
# ----------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
