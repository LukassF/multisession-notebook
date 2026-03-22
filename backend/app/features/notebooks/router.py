from fastapi import APIRouter, Depends
from app.features.auth.services.jwt_auth_guard import jwt_auth_guard
from sqlalchemy.orm import Session
from app.core.database.index import get_db
from app.features.notebooks.dto.create_notebook_dto import CreateNotebookDto
from app.features.notebooks.dto.append_to_notebook_dto import AppendToNotebookDto
from app.features.notebooks.services.create_notebook import create_notebook_service
from app.features.notebooks.services.poll_changes import poll_notebook_changes_service
from app.features.notebooks.services.append_to_notebook import (
    append_to_notebook_service,
)

notebooks = APIRouter(prefix="/api/notebooks", tags=["Notebooks"])


@notebooks.post("/")
async def create_notebook(
    data: CreateNotebookDto,
    auth_user_id: str = Depends(jwt_auth_guard),
    db: Session = Depends(get_db),
):
    try:
        created_notebook = create_notebook_service(db, data.title, auth_user_id)
        if not created_notebook:
            return {"message": "Notebook not created", "data": None}

        return {
            "message": "Notebook created successfully",
            "data": created_notebook.to_dict(),
        }
    except Exception as e:
        return {"message": "An error occurred", "error": str(e)}, 500


@notebooks.put("/{notebook_id}")
async def append_to_notebook(
    notebook_id: str,
    data: AppendToNotebookDto,
    auth_user_id: str = Depends(jwt_auth_guard),
    db: Session = Depends(get_db),
):
    try:
        result = await append_to_notebook_service(
            db, auth_user_id, notebook_id, data.content
        )
        return {"message": "Content update delegated", "data": result}
    except Exception as e:
        return {"message": "An error occurred", "error": str(e)}, 500


@notebooks.get("/{notebook_id}/poll")
async def poll_notebook_changes(
    notebook_id: str, auth_user_id: str = Depends(jwt_auth_guard)
):
    try:
        result = poll_notebook_changes_service(notebook_id)
        return {"message": "Poll successful", "data": result}
    except Exception as e:
        return {"message": "An error occurred", "error": str(e)}, 500
