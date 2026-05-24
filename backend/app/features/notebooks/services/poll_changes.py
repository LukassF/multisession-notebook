import os
import json
from app.core.errors.error_with_code import ErrorWithCode

DATA_DIR = "data"


def _assemble_text_from_event_chain(event_chain: list) -> str:
    if not isinstance(event_chain, list) or not event_chain:
        return ""

    ordered_chain = sorted(
        [entry for entry in event_chain if isinstance(entry, dict)],
        key=lambda entry: entry.get("server_version", 0),
    )

    buffer: list[str] = []
    for event in ordered_chain:
        op = event.get("op")
        index = event.get("char_start")
        if index is None:
            index = event.get("index", 0)
        try:
            index = int(index)
        except (TypeError, ValueError):
            index = 0

        text = event.get("text", "") or event.get("content", "") or ""
        length = int(event.get("length", 0) or 0)

        if op == "insert":
            insert_pos = max(0, min(len(buffer), index))
            buffer[insert_pos:insert_pos] = list(text)
        elif op == "delete":
            delete_end = min(len(buffer), index + length)
            if 0 <= index < delete_end:
                del buffer[index:delete_end]
        elif op == "replace":
            replace_end = min(len(buffer), index + length)
            if length > 0 and 0 <= index <= len(buffer):
                buffer[index:replace_end] = list(text)
            else:
                buffer = list(text)

    return "".join(buffer)


def poll_notebook_changes_service(notebook_uuid: str, auth_user_id: str):
    notebook_path = f"{DATA_DIR}/notebook_{notebook_uuid}"
    cache_file = f"{notebook_path}/cache.json"

    if not os.path.exists(notebook_path):
        raise ErrorWithCode("Notebook not found", 404)
    if not os.path.exists(cache_file):
        raise ErrorWithCode("Cache file not found for the notebook", 404)

    with open(cache_file, "r", encoding="utf-8") as f:
        cache_data: dict = json.load(f)
        metadata = (
            cache_data.get("metadata", {})
            if isinstance(cache_data.get("metadata"), dict)
            else {}
        )
        cache_notebook_id = cache_data.get("notebook_id") or metadata.get("notebook_id")
        if cache_notebook_id != notebook_uuid:
            raise ErrorWithCode("Cache data does not match the requested notebook", 400)

        admin_id = cache_data.get("admin_id") or metadata.get("admin_id")
        collaborators = (
            cache_data.get("collaborators") or metadata.get("collaborators") or []
        )

        # Normalize both to strings for comparison
        auth_user_id_str = str(auth_user_id) if auth_user_id else None
        admin_id_str = str(admin_id) if admin_id else None
        collaborators_str = [str(c) for c in collaborators]

        is_not_collaborator = (
            not collaborators_str or auth_user_id_str not in collaborators_str
        )

        # User has access if they are the admin OR if they are a collaborator
        if admin_id_str != auth_user_id_str and is_not_collaborator:
            raise ErrorWithCode("User does not have access to this notebook", 403)

        if "last_entries" in cache_data and "last_changes" not in cache_data:
            cache_data["last_changes"] = cache_data.get("last_entries", [])

        # Wczytaj pełną zawartość z content.json, aby poll mógł zwracać całe dane.
        content_path = f"{DATA_DIR}/notebook_{notebook_uuid}/content.json"
        full_content = ""
        if os.path.exists(content_path):
            try:
                with open(content_path, "r", encoding="utf-8") as content_file:
                    content_json = json.load(content_file)
                    event_chain = content_json.get("content_event_chain", [])
                    full_content = _assemble_text_from_event_chain(event_chain)
            except (FileNotFoundError, json.JSONDecodeError):
                full_content = ""

        cache_data["content"] = full_content
        return cache_data
