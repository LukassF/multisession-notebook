from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.kafka.producer_config import kafka_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[INFO] Initializing system services...")

    try:
        await kafka_manager.start()
    except Exception as e:
        print(f"[ERROR] Could not start Kafka Producer: {e}")

    yield

    print("[INFO] Shutting down system services...")
    await kafka_manager.stop()
