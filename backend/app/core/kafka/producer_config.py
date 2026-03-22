import os
import json
from aiokafka import AIOKafkaProducer
import asyncio

KAFKA_INSTANCE = None


class KafkaManager:
    def __init__(self):
        self.producer = None
        self.server = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")

    async def start(self):
        retries = 5
        while retries > 0:
            try:
                self.producer = AIOKafkaProducer(
                    bootstrap_servers=self.server,
                    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                    retry_backoff_ms=500,
                    request_timeout_ms=20000,
                )
                await self.producer.start()
                print("[KAFKA] Producer started successfully!", flush=True)
                return
            except Exception as e:
                retries -= 1
                print(
                    f"[KAFKA] Connection failed, retrying in 5s... ({retries} left). Error: {e}",
                    flush=True,
                )
                await asyncio.sleep(5)

        print("[KAFKA] Could not connect to Kafka after several retries.", flush=True)

    async def stop(self):
        if self.producer:
            await self.producer.stop()
            print("[KAFKA] Producer stopped")

    async def send_message(self, topic: str, message: dict):
        if self.producer:
            notebook_id = message.get("notebook_id")
            key_bytes = notebook_id.encode("utf-8") if notebook_id else None

            print(f"PRODUCER SENDING to {topic} with key {notebook_id}:", message)

            # ensure partition stability by using the notebook_id as the key
            await self.producer.send_and_wait(topic, value=message, key=key_bytes)
        else:
            print("[KAFKA ERROR] Producer not initialized - message not sent.")


kafka_manager = KafkaManager()
