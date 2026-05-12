import json
import time
import os
from kafka import KafkaConsumer
from app.workers.actors.notebook_actor import NotebookActor

KAFKA_SERVER = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
DATA_DIR = "/code/data"


class SessionManager:
    def __init__(self):
        self.active_sessions: dict[str, NotebookActor] = (
            {}
        )  # notebook_id -> NotebookActor

    def dispatch(self, message_value):
        try:
            data: dict = json.loads(message_value)
            nb_id = data.get("notebook_id")

            if not nb_id:
                return

            # create a new actor if this notebook_id doesn't have an active session
            if nb_id not in self.active_sessions:
                actor = NotebookActor(nb_id)
                self.active_sessions[nb_id] = actor
                # Start the actor thread to listen for tasks
                actor.start()

            self.active_sessions[nb_id].add_task(data)

        except Exception as e:
            print(f"[SESSION MANAGER ERROR] Dispatch failed: {e}")


if __name__ == "__main__":
    print("[WORKER] Session Manager is starting...")

    time.sleep(10)  # give Kafka some time to be ready

    consumer = KafkaConsumer(
        "notebook_updates",
        bootstrap_servers=KAFKA_SERVER,
        value_deserializer=lambda m: m.decode("utf-8"),
        group_id="session_manager_group",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )

    manager = SessionManager()

    print("[WORKER] Consumer is listening for tasks...")
    for message in consumer:
        print(f"[WORKER] Received message for notebook {message.value}")
        manager.dispatch(message.value)
