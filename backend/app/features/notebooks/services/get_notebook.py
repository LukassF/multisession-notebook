import os
import json
from sqlalchemy.orm import Session
from app.features.notebooks.models.notebook import Notebook
from app.core.errors.error_with_code import ErrorWithCode

DATA_DIR = "data"


def _read_full_notebook_json(notebook_uuid: str) -> dict:
    content_path = f"{DATA_DIR}/notebook_{notebook_uuid}/content.json"
    if not os.path.exists(content_path):
        return {}

    try:
        with open(content_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def get_notebook_service(db: Session, auth_user_id: str, notebook_id: str):
    notebook = db.query(Notebook).filter(Notebook.id == notebook_id).first()
    if not notebook:
        raise ErrorWithCode("Notebook not found", 404)

    is_not_collaborator = not notebook.collaborators or str(auth_user_id) not in [
        str(c) for c in notebook.collaborators
    ]
    if str(notebook.admin_id) != str(auth_user_id) and is_not_collaborator:
        raise ErrorWithCode("User does not have access to this notebook", 403)

    content_json = _read_full_notebook_json(notebook_id)
    return content_json
