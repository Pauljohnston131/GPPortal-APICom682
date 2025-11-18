import os
from azure.cosmos import CosmosClient, PartitionKey

def get_container():
    client = CosmosClient(os.environ["COSMOS_URL"], os.environ["COSMOS_KEY"])
    db_name = os.environ.get("COSMOS_DB", "gpportal")
    c_name = os.environ.get("COSMOS_CONTAINER", "records")

    # Get or create DB
    try:
        db = client.create_database_if_not_exists(id=db_name)
    except Exception:
        db = client.get_database_client(db_name)

    # Get or create container (partition on patientId)
    try:
        cont = db.create_container_if_not_exists(
            id=c_name,
            partition_key=PartitionKey(path="/patientId")
        )
    except Exception:
        cont = db.get_container_client(c_name)

    return cont


def upsert_record(doc: dict):
    cont = get_container()
    return cont.upsert_item(doc)


def list_records(patient_id: str, limit: int = 50):
    cont = get_container()
    query = "SELECT * FROM c WHERE c.patientId = @p ORDER BY c._ts DESC"
    params = [{"name": "@p", "value": patient_id}]
    items = list(
        cont.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=True
        )
    )
    return items[:limit]


def get_record_by_id(record_id: str):
    """
    Fetch a single record by its id (across all patients).
    """
    cont = get_container()
    query = "SELECT * FROM c WHERE c.id = @id"
    params = [{"name": "@id", "value": record_id}]
    items = list(
        cont.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=True
        )
    )
    return items[0] if items else None


def update_record_by_id(record_id: str, updates: dict):
    """
    Merge updates (e.g. status, gpNotes) into an existing record.
    """
    cont = get_container()
    doc = get_record_by_id(record_id)
    if not doc:
        return None

    doc.update(updates)

    # replace existing item
    cont.replace_item(item=doc["id"], body=doc)
    return doc
