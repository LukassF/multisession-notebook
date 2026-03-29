import threading
import time
import queue
from typing import Any, Dict, List, TypedDict
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


class NotebookActor(threading.Thread):
    def __init__(self, notebook_id: str):
        super().__init__(daemon=True)
        self.notebook_id = notebook_id
        # Each actor has its own queue for receiving tasks
        self.task_queue = queue.Queue()

        self.context: Context = {
            "model_version": "v1-embedding",
            "settings": {"auto_save": True, "encoding": "utf-8"},
            "cache": [],  # Last 5 changes for quick access
            "start_time": time.time(),
        }

    def _write_to_file(self, task: Dict[str, Any]):
        filename = f"data/notebook_{self.notebook_id}/content.txt"
        encoding = self.context["settings"]["encoding"]
        with open(filename, "a", encoding=encoding) as f:
            f.write(task["content"] + "\n")

    def _update_cache_and_json(self, task: Dict[str, Any]):
        new_entry: CacheEntry = {
            "content": task.get("content", ""),
            "author_id": task.get("user_id", "unknown"),
            "timestamp": task.get("timestamp", time.time()),
        }

        self.context["cache"].append(new_entry)
        if len(self.context["cache"]) > 5:
            self.context["cache"].pop(0)

        # Konstruuj pełną zawartość z wszystkich zmian lub użyj bezpośrednio
        full_content = task.get("content", "")

        cache_path = f"data/notebook_{self.notebook_id}/cache.json"
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "notebook_id": self.notebook_id,
                    "title": task.get("title", "Notatnik"),
                    "content": full_content,  # ← DODANE: pełna zawartość dla /poll
                    "model_version": self.context["model_version"],
                    "last_changes": self.context["cache"],
                    "admin_id": task.get("admin_id", "unknown"),
                    "collaborators": task.get("collaborators", []),
                    "updated_at": time.time(),
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
                self._write_to_file(task)
                self._update_cache_and_json(task)
            except Exception as e:
                print(f"[!] Error writing to session {self.notebook_id}: {e}")
            finally:
                self.task_queue.task_done()

    def add_task(self, task: Dict[str, Any]):
        self.task_queue.put(task)
