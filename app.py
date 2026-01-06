# ----------------------------------------------------------
# COM682 Coursework 2 – Multimedia GP Portal (Cloud-Native)
# Flask API for file upload & record management
# Author: Paul Johnston (B00888517)
# ----------------------------------------------------------

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify
from flask import Response
from services.storage import download_blob_bytes
from flask_cors import CORS
from services.storage import upload_bytes
from services.storage import delete_blob
from services.cosmos import (
    upsert_record,
    list_records,
    get_record_by_id,
    update_record_by_id,
    delete_record_by_id,
    search_patient_ids,
)
import os
import uuid
import time
import logging
import requests

UPLOAD_LOGIC_APP_URL = os.environ.get("UPLOAD_LOGIC_APP_URL")
REVIEW_LOGIC_APP_URL = os.environ.get("REVIEW_LOGIC_APP_URL")
AUDIT_LOGIC_APP_URL = os.environ.get("AUDIT_LOGIC_APP_URL")
AI_LOGIC_APP_URL = os.environ.get("AI_LOGIC_APP_URL")


# ----------------------------------------------------------
# Flask setup + CORS
# ----------------------------------------------------------
app = Flask(__name__)

# Allow all origins for dev (file://, localhost, Static Web App, etc.)
CORS(app, resources={r"/*": {"origins": "*"}})

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gpportal-api")


# ----------------------------------------------------------
# Helpers
# ----------------------------------------------------------
def json_error(message: str, status_code: int):
    resp = jsonify({"error": message})
    resp.status_code = status_code
    return resp


# ----------------------------------------------------------
# Health check endpoint
# ----------------------------------------------------------
@app.get("/health")
def health():
    logger.info("Health check called")
    return jsonify({"status": "ok", "service": "gpportal-api"}), 200


# ----------------------------------------------------------
# Upload endpoint (Patient Portal)
# ----------------------------------------------------------
@app.post("/upload")
def upload():
    """
    Accepts multipart/form-data:
      - patientId (string)
      - file (image/pdf/etc)
    Stores file in Blob Storage and metadata in Cosmos DB.
    """
    if "files" not in request.files:
        return json_error("file missing", 400)

    file = request.files.get("files")
    patient_id = (request.form.get("patientId") or "").strip()

    if not patient_id:
        return json_error("patientId required", 400)

    # Generate unique blob name: patientId/uuid.ext
    ext = (file.filename or "file").split(".")[-1].lower()
    blob_name = f"{patient_id}/{uuid.uuid4()}.{ext}"

    # Upload to Blob Storage
    try:
        blob_url = upload_bytes(blob_name, file.read(), file.mimetype)
    except Exception as e:
        logger.error(f"Blob upload failed: {e}")
        return json_error("upload failed", 500)

    # Create a Cosmos DB record
    record = {
        "id": str(uuid.uuid4()),
        "patientId": patient_id,
        "blobUrl": blob_url,
        "blobName": blob_name,
        "originalName": file.filename,
        "contentType": file.mimetype,
        "status": "pending",
        "gpNotes": "",
        "createdAt": int(time.time()),
    }

    try:
        upsert_record(record)
    except Exception as e:
        logger.error(f"Cosmos upsert failed: {e}")
        return json_error("database error", 500)

    # Trigger Upload Logic App (email / audit)
    if UPLOAD_LOGIC_APP_URL:
        try:
            requests.post(
    AI_LOGIC_APP_URL,
    json={
        "recordId": record["id"],
        "patientId": record["patientId"],
        "blobUrl": record["blobUrl"],
        "contentType": record["contentType"]
    },
    headers={"Content-Type": "application/json"},
    timeout=5
)

        except Exception as e:
            logger.warning(f"Upload Logic App trigger failed: {e}")

    # Trigger AI Logic App (Computer Vision)
    if AI_LOGIC_APP_URL:
        try:
            requests.post(
                AI_LOGIC_APP_URL,
                json={
                    "recordId": record["id"],
                    "patientId": record["patientId"],
                    "blobUrl": record["blobUrl"]
                },
                headers={"Content-Type": "application/json"},
                timeout=5
            )
        except Exception as e:
            logger.warning(f"AI Logic App trigger failed: {e}")

    logger.info(f"File uploaded for patient {patient_id}")

    return jsonify(
        {
            "message": "uploaded",
            "record": record,
        }
    ), 201



# ----------------------------------------------------------
# Retrieve patient records (Patient Portal + GP Dashboard)
# ----------------------------------------------------------
@app.get("/records")
def records():
    """
    GET /records?patientId=...
    Returns all records for a given patientId.
    """
    patient_id = request.args.get("patientId", "").strip()
    if not patient_id:
        return json_error("patientId query param required", 400)

    try:
        items = list_records(patient_id)
        return jsonify(
            {
                "patientId": patient_id,
                "count": len(items),
                "records": items,
            }
        ), 200
    except Exception as e:
        logger.error(f"Error fetching records for {patient_id}: {e}")
        return json_error("failed to fetch records", 500)


# ----------------------------------------------------------
# Get a single record by id (GP detail view)
# ----------------------------------------------------------
@app.get("/record/<record_id>")
def get_record(record_id):
    try:
        rec = get_record_by_id(record_id)
        if not rec:
            return json_error("record not found", 404)
        return jsonify(rec), 200
    except Exception as e:
        logger.error(f"Error fetching record {record_id}: {e}")
        return json_error("failed to fetch record", 500)


@app.put("/record/<record_id>")
def update_record(record_id):
    """
    Body (JSON), any of:
      - status: string
      - gpNotes: string
      - aiTags: list of strings
    """
    data = request.get_json(silent=True) or {}

    updates = {}

    if "status" in data:
        updates["status"] = str(data["status"]).strip()

    if "gpNotes" in data:
        updates["gpNotes"] = str(data["gpNotes"]).strip()

    if "aiTags" in data:
        updates["aiTags"] = data["aiTags"]

    if not updates:
        return json_error("no fields to update", 400)

    updates["updatedAt"] = int(time.time())

    try:
        updated = update_record_by_id(record_id, updates)
        if not updated:
            return json_error("record not found", 404)

        # Trigger Logic App if reviewed
        if updates.get("status") == "reviewed" and REVIEW_LOGIC_APP_URL:
            try:
                logger.info(f"Sending review event to Logic App: record={record_id}, status={updates.get('status')}")
                requests.post(
                    REVIEW_LOGIC_APP_URL,
                    json={
                        "recordId": record_id,
                        "patientId": updated["patientId"],
                        "status": "reviewed",
                        "updatedAt": updates["updatedAt"]
                    },
                    headers={"Content-Type": "application/json"}
                )
            except Exception as e:
                logger.warning(f"Review Logic App trigger failed: {e}")

        return jsonify(updated), 200

    except Exception as e:
        logger.error(f"Error updating record {record_id}: {e}")
        return json_error("failed to update record", 500)

# ----------------------------------------------------------
# Delete a record (GP-only action in future)
# ----------------------------------------------------------
@app.delete("/record/<record_id>")
def delete_record(record_id):
    try:
        rec = get_record_by_id(record_id)
        if not rec:
            return json_error("record not found", 404)

        # Delete blob from storage
        delete_blob(rec["blobName"])

        # Delete metadata from Cosmos DB
        delete_record_by_id(record_id)

        # Trigger audit Logic App
        if AUDIT_LOGIC_APP_URL:
            try:
                import requests
                requests.post(
                    AUDIT_LOGIC_APP_URL,
                    json={
                        "recordId": record_id,
                        "patientId": rec["patientId"],
                        "action": "deleted",
                        "timestamp": int(time.time())
                    },
                    headers={"Content-Type": "application/json"}
                )
            except Exception as e:
                logger.warning(f"Audit Logic App trigger failed: {e}")

        return jsonify({"message": "record and blob deleted"}), 200

    except Exception as e:
        logger.error(f"Error deleting record {record_id}: {e}")
        return json_error("failed to delete record", 500)




# ----------------------------------------------------------
# Search patients by partial ID (for future autocomplete)
# ----------------------------------------------------------
@app.get("/search/patients")
def search_patients():
    """
    GET /search/patients?query=P0
    Returns distinct patientIds containing the query string.
    """
    query = request.args.get("query", "").strip()
    if not query:
        return json_error("query param required", 400)

    try:
        ids = search_patient_ids(query)
        return jsonify({"results": ids}), 200
    except Exception as e:
        logger.error(f"Error searching patients for query '{query}': {e}")
        return json_error("failed to search patients", 500)



@app.get("/media/<path:blob_path>")
def media(blob_path):
    try:
        data, content_type = download_blob_bytes(blob_path)
        return Response(data, mimetype=content_type)
    except Exception as e:
        return jsonify({"error": "Blob not found"}), 404
    
@app.get("/debug/list-blobs")
def list_blobs():
    from azure.storage.blob import BlobServiceClient
    conn = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    container = os.environ.get("BLOB_CONTAINER", "patient-uploads")
    service = BlobServiceClient.from_connection_string(conn)
    container_client = service.get_container_client(container)
    blobs = list(container_client.list_blobs(name_starts_with="P004/"))
    blob_names = [blob.name for blob in blobs]
    return jsonify({"container": container, "blobs_for_P004": blob_names}), 200
# ----------------------------------------------------------
# Entry point
# ----------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
