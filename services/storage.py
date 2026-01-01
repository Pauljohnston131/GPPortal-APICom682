# services/storage.py
import os
from azure.storage.blob import BlobServiceClient, ContentSettings

# -------------------------------
# CONNECT TO STORAGE
# -------------------------------
def get_container_client():
    conn = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    container = os.environ.get("BLOB_CONTAINER", "patient-uploads")
    service = BlobServiceClient.from_connection_string(conn)
    return service.get_container_client(container)

def get_blob_client(blob_name: str):
    container = get_container_client()
    return container.get_blob_client(blob_name)

# -------------------------------
# UPLOAD
# -------------------------------
def upload_bytes(name: str, data: bytes, content_type: str = None):
    blob = get_blob_client(name)
    settings = ContentSettings(content_type=content_type) if content_type else None
    blob.upload_blob(data, overwrite=True, content_settings=settings)
    return blob.url

# -------------------------------
# DELETE
# -------------------------------
def delete_blob(blob_name: str):
    blob = get_blob_client(blob_name)
    blob.delete_blob()

# -------------------------------
# DOWNLOAD FOR IMAGE PREVIEW — FIXED
# -------------------------------
def download_blob_bytes(blob_name: str):
    # blob_name is exactly the relative path inside container, e.g. "P004/abc123.jpeg"
    # NO prefixing! Your previous bug is gone.
    blob = get_blob_client(blob_name)
    data = blob.download_blob().readall()
    props = blob.get_blob_properties()
    content_type = props.content_settings.content_type or "application/octet-stream"
    return data, content_type