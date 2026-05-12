import threading
import time
import queue
from typing import Any, Dict, List, Optional, TypedDict
import json


class CacheEntry(TypedDict):
    content: str
    author_id: str
    timestamp: float


class Context(TypedDict):
    model_version: str
    settings: Dict[str, Any]
    cache: List[CacheEntry]
    start_time: float


class ContentJson(TypedDict):
    title: str
    metadata: Dict[str, Any]
    content_event_chain: List[CacheEntry]
    version: int


class ContentEntry(TypedDict):
    op: str  # insert | delete | replace
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    text: Optional[str] = None
    base_version: Optional[int] = None
    change_id: Optional[str] = None


class NotebookActor(threading.Thread):
    def __init__(self, notebook_id: str):
        super().__init__(daemon=True)
        self.notebook_id = notebook_id
        # Each actor has its own queue for receiving tasks
        self.task_queue = queue.Queue()

        self.context: Context = {
            "model_version": "v1-embedding",
            "settings": {"auto_save": True, "encoding": "utf-8"},
            "cache": [],  # Last 10 changes for quick access
            "start_time": time.time(),
        }

    def _update_content(self, task: Dict[str, Any]):
        filename = f"data/notebook_{self.notebook_id}/content.json"
        encoding = self.context["settings"]["encoding"]

        # Przygotuj obiekt zmiany z oczekiwanymi polami (delta)
        change_entry: ContentEntry = {
            "op": task.get(
                "op", "insert"
            ),  # domyślnie "insert", ale może być "delete" lub "replace"
            "line_start": task.get("line_start"),  # optional
            "line_end": task.get("line_end"),  # optional
            "char_start": task.get("char_start"),  # optional
            "char_end": task.get("char_end"),  # optional
            "text": task.get(
                "content", ""
            ),  # optional, zawartość do wstawienia lub zastąpienia
            "author_id": task.get("user_id", "unknown"),
            "timestamp": task.get("timestamp", time.time()),
            "base_version": task.get(
                "base_version"
            ),  # wersja klienta, do walidacji konfliktów
            "change_id": task.get("change_id"),
        }

        # Przeczytaj istniejący plik
        try:
            with open(filename, "r", encoding=encoding) as f:
                data: ContentJson = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {
                "title": task.get("title", "Notatnik"),
                "metadata": {
                    "title": task.get("title", "Notatnik"),
                    "notebook_id": self.notebook_id,
                    "admin_id": task.get("admin_id", "unknown"),
                    "collaborators": task.get("collaborators", []),
                    "updated_at": time.time(),
                    "model_version": self.context["model_version"],
                },
                "version": 0,
                "content_event_chain": [],
            }

        # Walidacja wersji klienta (base_version)
        client_base = change_entry.get("base_version")
        server_version = data.get("version", 0)
        if client_base is not None and client_base != server_version:
            # Niezgodność wersji — nadal zapisujemy zmianę, ale oznaczamy konflikt flagą
            change_entry["base_version_mismatch"] = True

        # Nadaj numer wersji po stronie serwera (ciągły seq)
        new_version = server_version + 1
        change_entry["server_version"] = new_version

        # Dodaj zmianę i zaktualizuj metadane dokumentu
        data.setdefault("content_event_chain", []).append(change_entry)
        data["version"] = new_version
        data["last_updated"] = time.time()

        # Zapisz z powrotem
        with open(filename, "w", encoding=encoding) as f:
            json.dump(data, f, indent=4)

    def _update_cache(self, task: Dict[str, Any]):
        new_entry: CacheEntry = {
            "content": task.get("content", ""),
            "author_id": task.get("user_id", "unknown"),
            "timestamp": task.get("timestamp", time.time()),
        }

        self.context["cache"].append(new_entry)
        if len(self.context["cache"]) > 10:  # Keep only last 10 changes in cache
            self.context["cache"].pop(0)

        cache_path = f"data/notebook_{self.notebook_id}/cache.json"
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "title": task.get("title", "Notatnik"),
                    "metadata": {
                        "title": task.get("title", "Notatnik"),
                        "notebook_id": self.notebook_id,
                        "admin_id": task.get("admin_id", "unknown"),
                        "collaborators": task.get("collaborators", []),
                        "model_version": self.context["model_version"],
                        "updated_at": time.time(),
                    },
                    "last_changes": self.context["cache"],
                },
                f,
                indent=4,
            )

    def run(self):
        print(
            f"[*] Actor for notebook {self.notebook_id} started and waiting for tasks..."
        )
        while True:
            # listen for incoming tasks (blocking call)
            task = self.task_queue.get()

            try:
                self._update_content(task)
                self._update_cache(task)
            except Exception as e:
                print(f"[!] Error writing to session {self.notebook_id}: {e}")
            finally:
                self.task_queue.task_done()

    def add_task(self, task: Dict[str, Any]):
        self.task_queue.put(task)
