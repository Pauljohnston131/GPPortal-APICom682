from azure.storage.blob import BlobServiceClient, ContentSettings
import os

def get_blob_client():
    conn = os.environ["AZURE_STORAGE_CONN_STRING"]
    svc = BlobServiceClient.from_connection_string(conn)
    container = os.environ.get("AZURE_STORAGE_CONTAINER", "uploads")
    return svc.get_container_client(container)

def upload_bytes(name: str, data: bytes, content_type: str = None):
    container = get_blob_client()
    try:
        container.create_container()
    except Exception:
        pass

    blob = container.get_blob_client(name)
    settings = ContentSettings(content_type=content_type) if content_type else None

    blob.upload_blob(
        data,
        overwrite=True,
        content_settings=settings
    )

    return blob.url
