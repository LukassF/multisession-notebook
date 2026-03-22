from fastapi import FastAPI
from app.core.database.seed import seed
from app.features.auth.router import auth
from app.features.users.router import users
from app.features.notebooks.router import notebooks
from app.core.lifespan import lifespan
import asyncio


def create_app():
    app = FastAPI(lifespan=lifespan)
    seed()
    app.include_router(auth)
    app.include_router(users)
    app.include_router(notebooks)

    return app

    # KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    # TOPIC = "notebook_events"

    # producer = None

    # @app.on_event("startup")
    # async def startup_event():
    #     global producer
    #     producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
    #     await producer.start()

    # @app.on_event("shutdown")
    # async def shutdown_event():
    #     await producer.stop()

    # @app.post("/sessions/{session_id}/append")
    # async def append_to_notebook(session_id: str, content: str):
    #     payload = {"session_id": session_id, "content": content}

    #     # Wysyłamy do Kafki. Kluczem (key) jest session_id,
    #     # dzięki czemu Kafka zawsze wyśle to do tej samej partycji/workera.
    #     await producer.send_and_wait(
    #         TOPIC, key=session_id.encode(), value=json.dumps(payload).encode()
    #     )

    #     return {"status": "Sent to queue", "session_id": session_id}


app = create_app()


@app.get("/")
async def root():
    return {
        "message": "Hello World! Notatnik API działa.",
        "docs": "Wejdź na /docs żeby zobaczyć dokumentację Swagger",
    }
