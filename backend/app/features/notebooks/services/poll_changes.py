import os
import json

DATA_DIR = "data"


def poll_notebook_changes_service(notebook_uuid: str):
    notebook_path = f"{DATA_DIR}/notebook_{notebook_uuid}"
    cache_file = f"{notebook_path}/cache.json"

    if not os.path.exists(notebook_path):
        raise FileNotFoundError("Notebook not found")
    if not os.path.exists(cache_file):
        raise FileNotFoundError("Cache file not found for the notebook")

    with open(cache_file, "r", encoding="utf-8") as f:
        cache_data = json.load(f)
        return {"status": "active", "data": cache_data}
