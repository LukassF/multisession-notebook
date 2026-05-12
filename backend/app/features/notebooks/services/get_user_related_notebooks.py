from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.features.notebooks.models.notebook import Notebook


def get_user_related_notebooks_service(
    db: Session, user_id: str
) -> List[Dict[str, Any]]:
    """Return list of notebooks where user is admin or in collaborators.

    For compatibility across DB backends we load all notebooks and filter in Python.
    If you have large number of notebooks, replace with DB-specific JSON query.
    """
    result = []
    all_nbs = db.query(Notebook).all()
    for nb in all_nbs:
        try:
            collabs = nb.collaborators or []
        except Exception:
            collabs = []

        if str(nb.admin_id) == str(user_id) or str(user_id) in [
            str(c) for c in collabs
        ]:
            result.append(nb.to_dict())

    return result
