import os
import shutil
from sqlalchemy.orm import Session
from app.features.notebooks.models.notebook import Notebook
from app.core.errors.error_with_code import ErrorWithCode

DATA_DIR = "data"


def delete_notebook_service(db: Session, auth_user_id: str, notebook_id: str):
    """Delete a notebook if the user is the admin."""
    notebook = db.query(Notebook).filter(Notebook.id == notebook_id).first()
    if not notebook:
        raise ErrorWithCode("Notebook not found", 404)

    # Only the admin can delete the notebook
    if str(notebook.admin_id) != str(auth_user_id):
        raise ErrorWithCode("Only the notebook admin can delete it", 403)

    try:
        # Delete from database
        db.delete(notebook)
        db.commit()

        # Delete the data directory
        notebook_path = f"{DATA_DIR}/notebook_{notebook_id}"
        if os.path.exists(notebook_path):
            shutil.rmtree(notebook_path)

        return notebook_id

    except Exception as e:
        db.rollback()
        raise ErrorWithCode(f"Failed to delete notebook: {str(e)}", 500)
