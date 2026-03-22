from sqlalchemy.orm import Session
from app.features.notebooks.models.notebook import Notebook
from app.features.users.models.user import User
from sqlalchemy.orm.attributes import flag_modified
from app.core.kafka.producer_config import kafka_manager
import time
from app.core.errors.error_with_code import ErrorWithCode


async def invite_to_notebook_service(
    db: Session, auth_user_id: str, notebook_id: str, emails: list[str]
):
    try:
        notebook = db.query(Notebook).filter(Notebook.id == notebook_id).first()
        if not notebook:
            raise ErrorWithCode("Notebook not found", 404)

        if str(notebook.admin_id) != str(auth_user_id):
            raise ErrorWithCode("Only admin can invite collaborators", 403)

        users = db.query(User).filter(User.email.in_(emails)).all()
        new_ids = [u.id for u in users]

        if not new_ids:
            raise ErrorWithCode("No valid users found for the provided emails", 400)

        current_collabs = set(notebook.collaborators or [])
        updated_collabs = list(current_collabs.union(new_ids))

        notebook.collaborators = updated_collabs

        # make SQLAlchemy aware of the change in the JSON column
        flag_modified(notebook, "collaborators")

        db.commit()
        db.refresh(notebook)

        payload = {
            "notebook_id": notebook_id,
            "content": "",
            "user_id": auth_user_id,
            # track updates in collaborators and admin_id to save the state in cache
            # to avoid hitting the database with access control checks when polling for updates
            "admin_id": notebook.admin_id,
            "collaborators": notebook.collaborators or [],
            "timestamp": time.time(),
        }

        await kafka_manager.send_message("notebook_updates", payload)

        return notebook.collaborators

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Invitation failed: {e}")
        raise e
