from app.core.kafka.producer_config import kafka_manager
import time
from sqlalchemy.orm import Session
from app.features.notebooks.models.notebook import Notebook
from app.core.errors.error_with_code import ErrorWithCode


async def append_to_notebook_service(
    db: Session, auth_user_id: str, notebook_id: str, content: str
):
    notebook = db.query(Notebook).filter(Notebook.id == notebook_id).first()
    if not notebook:
        raise ErrorWithCode("Notebook not found", 404)

    is_not_collaborator = not notebook.collaborators or str(auth_user_id) not in [
        str(c) for c in notebook.collaborators
    ]

    if str(notebook.admin_id) != str(auth_user_id) and is_not_collaborator:
        raise ErrorWithCode("Only admin or collaborators can append to notebook", 403)

    payload = {
        "notebook_id": notebook_id,
        "content": content,
        "user_id": auth_user_id,
        # track updates in collaborators and admin_id to save the state in cache
        # to avoid hitting the database with access control checks when polling for updates
        "admin_id": notebook.admin_id,
        "collaborators": notebook.collaborators or [],
        "timestamp": time.time(),
    }

    await kafka_manager.send_message("notebook_updates", payload)

    return notebook_id
