import os
from typing import List, Dict, Optional
from azure.cosmos import CosmosClient, PartitionKey


def _get_client() -> CosmosClient:
    url = os.environ["COSMOS_URL"]
    key = os.environ["COSMOS_KEY"]
    return CosmosClient(url, credential=key)


def get_container():
    client = _get_client()
    db_name = os.environ.get("COSMOS_DB", "gpportal")
    container_name = os.environ.get("COSMOS_CONTAINER", "records")

    # Get or create DB
    try:
        db = client.create_database_if_not_exists(id=db_name)
    except Exception:
        db = client.get_database_client(db_name)

    # Get or create container (partition on patientId)
    try:
        container = db.create_container_if_not_exists(
            id=container_name,
            partition_key=PartitionKey(path="/patientId"),
        )
    except Exception:
        container = db.get_container_client(container_name)

    return container


# ----------------------------------------------------------
# Basic operations
# ----------------------------------------------------------
def upsert_record(doc: Dict) -> Dict:
    container = get_container()
    return container.upsert_item(doc)


def list_records(patient_id: str, limit: int = 50) -> List[Dict]:
    container = get_container()
    query = "SELECT * FROM c WHERE c.patientId = @p ORDER BY c._ts DESC"
    params = [{"name": "@p", "value": patient_id}]
    items = list(
        container.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=True,
        )
    )
    return items[:limit]


def get_record_by_id(record_id: str) -> Optional[Dict]:
    """
    Fetch a single record by its id (across all patient partitions).
    """
    container = get_container()
    query = "SELECT * FROM c WHERE c.id = @id"
    params = [{"name": "@id", "value": record_id}]
    items = list(
        container.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=True,
        )
    )
    return items[0] if items else None


def update_record_by_id(record_id: str, updates: Dict) -> Optional[Dict]:
    """
    Merge updates into existing record and replace item in Cosmos.
    """
    container = get_container()
    doc = get_record_by_id(record_id)
    if not doc:
        return None

    doc.update(updates)
    container.replace_item(item=doc["id"], body=doc)
    return doc


def delete_record_by_id(record_id: str) -> bool:
    """
    Delete an existing record by id + partition key (patientId).
    Returns True if deleted, False if not found.
    """
    container = get_container()
    doc = get_record_by_id(record_id)
    if not doc:
        return False

    container.delete_item(item=doc["id"], partition_key=doc["patientId"])
    return True


def search_patient_ids(query_text: str, limit: int = 10) -> List[str]:
    """
    Return distinct patientIds containing the query_text (case-insensitive).
    Useful for autocomplete in GP dashboard.
    """
    container = get_container()
    # Basic CONTAINS search on patientId
    query = "SELECT DISTINCT VALUE c.patientId FROM c WHERE CONTAINS(LOWER(c.patientId), LOWER(@q))"
    params = [{"name": "@q", "value": query_text}]

    items = list(
        container.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=True,
        )
    )
    # items are already plain string values (patientId)
    return items[:limit]
