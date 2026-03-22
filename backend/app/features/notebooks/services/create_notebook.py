import uuid
import os
from sqlalchemy.orm import Session
from app.features.notebooks.models.notebook import Notebook
import json
from app.core.errors.error_with_code import ErrorWithCode

DATA_DIR = "data"


def create_notebook_service(db: Session, title: str, admin_id: int):
    notebook_uuid = str(uuid.uuid4())

    new_nb = Notebook(id=notebook_uuid, title=title, admin_id=admin_id)

    try:
        db.add(new_nb)

        notebook_path = f"{DATA_DIR}/notebook_{notebook_uuid}"

        if not os.path.exists(notebook_path):
            os.makedirs(notebook_path)

        file_path = f"{notebook_path}/content.txt"

        with open(file_path, "x", encoding="utf-8") as f:
            f.write(f"Notebook: {title}\nCreated by: {admin_id}\n---\n")

        cache_path = f"{notebook_path}/cache.json"
        initial_cache = {
            "notebook_id": notebook_uuid,
            "last_entries": [],
        }
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(initial_cache, f)

        db.commit()
        db.refresh(new_nb)
        return new_nb

    except Exception as e:
        db.rollback()

        if "file_path" in locals() and os.path.exists(file_path):
            os.remove(file_path)

        raise ErrorWithCode(f"Failed to create notebook and file: {str(e)}", 500)
