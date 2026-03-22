from app.core.kafka.producer_config import kafka_manager
import time
from sqlalchemy.orm import Session
from app.features.notebooks.models.notebook import Notebook


async def append_to_notebook_service(
    db: Session, auth_user_id: str, notebook_id: str, content: str
):
    notebook = db.query(Notebook).filter(Notebook.id == notebook_id).first()
    if not notebook:
        return {"message": "Notebook not found"}, 404

    payload = {
        "notebook_id": notebook_id,
        "content": content,
        "user_id": auth_user_id,
        "timestamp": time.time(),
    }

    await kafka_manager.send_message("notebook_updates", payload)

    # 202 accepted - indicatesthat the request has been accepted for processing,
    # but the processing has not been completed. This is appropriate here since
    # we're sending the update to a worker and we don't know when it will be processed.
    return {"status": "sent_to_worker", "notebook_id": notebook_id}, 202
