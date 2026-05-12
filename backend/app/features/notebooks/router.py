from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from app.features.auth.services.jwt_auth_guard import jwt_auth_guard
from sqlalchemy.orm import Session
from app.core.database.index import get_db
from app.features.notebooks.dto.create_notebook_dto import CreateNotebookDto
from app.features.notebooks.dto.append_to_notebook_dto import AppendToNotebookDto
from app.features.notebooks.dto.invite_to_notebook_dto import InviteToNotebookDto
from app.features.notebooks.services.create_notebook import create_notebook_service
from app.features.notebooks.services.poll_changes import poll_notebook_changes_service
from app.features.notebooks.services.append_to_notebook import (
    append_to_notebook_service,
)
from app.features.notebooks.services.invite_to_notebook import (
    invite_to_notebook_service,
)
from app.core.errors.error_with_code import ErrorWithCode
from app.features.notebooks.services.get_user_related_notebooks import (
    get_user_related_notebooks_service,
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

        return JSONResponse(
            status_code=201,
            content={
                "message": "Notebook created successfully",
                "data": created_notebook.to_dict(),
            },
        )
    except Exception as e:
        return HTTPException(
            detail={
                "message": "An error occurred while creating notebook",
                "error": str(e),
            },
            status_code=e.code if isinstance(e, ErrorWithCode) else 500,
        )


@notebooks.put("/{notebook_id}/invite")
async def invite_to_notebook(
    notebook_id: str,
    data: InviteToNotebookDto,
    auth_user_id: str = Depends(jwt_auth_guard),
    db: Session = Depends(get_db),
):
    try:
        result = await invite_to_notebook_service(
            db, auth_user_id, notebook_id, data.emails
        )
        return JSONResponse(
            status_code=200, content={"message": "Invitations sent", "data": result}
        )
    except Exception as e:
        return HTTPException(
            detail={
                "message": "An error occurred while sending invitations",
                "error": str(e),
            },
            status_code=e.code if isinstance(e, ErrorWithCode) else 500,
        )


@notebooks.put("/{notebook_id}")
async def append_to_notebook(
    notebook_id: str,
    data: AppendToNotebookDto,
    auth_user_id: str = Depends(jwt_auth_guard),
    db: Session = Depends(get_db),
):
    try:
        notebook_id_res = await append_to_notebook_service(
            db, auth_user_id, notebook_id, data.content
        )

        # 202 accepted - indicatesthat the request has been accepted for processing,
        # but the processing has not been completed. This is appropriate here since
        # we're sending the update to a worker and we don't know when it will be processed.
        return JSONResponse(
            status_code=202,
            content={"message": "Content update delegated", "data": notebook_id_res},
        )
    except Exception as e:
        return HTTPException(
            detail={
                "message": "An error occurred while appending to notebook",
                "error": str(e),
            },
            status_code=e.code if isinstance(e, ErrorWithCode) else 500,
        )


@notebooks.get("/{notebook_id}/poll")
async def poll_notebook_changes(
    notebook_id: str, auth_user_id: str = Depends(jwt_auth_guard)
):
    try:
        result = poll_notebook_changes_service(notebook_id, auth_user_id)
        return JSONResponse(
            status_code=200, content={"message": "Poll successful", "data": result}
        )
    except Exception as e:
        return HTTPException(
            detail={
                "message": "An error occurred while polling notebook changes",
                "error": str(e),
            },
            status_code=e.code if isinstance(e, ErrorWithCode) else 500,
        )


@notebooks.get("/")
async def list_user_notebooks(
    auth_user_id: str = Depends(jwt_auth_guard), db: Session = Depends(get_db)
):
    try:
        result = get_user_related_notebooks_service(db, auth_user_id)
        return JSONResponse(
            status_code=200, content={"message": "Notebooks fetched", "data": result}
        )
    except Exception as e:
        return HTTPException(
            detail={
                "message": "An error occurred while fetching notebooks",
                "error": str(e),
            },
            status_code=e.code if isinstance(e, ErrorWithCode) else 500,
        )
