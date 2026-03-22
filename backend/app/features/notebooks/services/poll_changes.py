import os
import json
from app.core.errors.error_with_code import ErrorWithCode

DATA_DIR = "data"


def poll_notebook_changes_service(notebook_uuid: str, auth_user_id: str):
    notebook_path = f"{DATA_DIR}/notebook_{notebook_uuid}"
    cache_file = f"{notebook_path}/cache.json"

    if not os.path.exists(notebook_path):
        raise ErrorWithCode("Notebook not found", 404)
    if not os.path.exists(cache_file):
        raise ErrorWithCode("Cache file not found for the notebook", 404)

    with open(cache_file, "r", encoding="utf-8") as f:
        cache_data: dict = json.load(f)
        if cache_data.get("notebook_id") != notebook_uuid:
            raise ErrorWithCode("Cache data does not match the requested notebook", 400)

        admin_id = cache_data.get("admin_id")
        collaborators = cache_data.get("collaborators", [])
        is_not_collaborator = not collaborators or str(auth_user_id) not in [
            str(c) for c in collaborators
        ]
        if admin_id != auth_user_id and is_not_collaborator:
            raise ErrorWithCode("User does not have access to this notebook", 403)

        return cache_data
