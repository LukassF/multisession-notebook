from app.core.database.index import Base, engine

import app.features.users.models.user
import app.features.auth.models.refresh_token
import app.features.notebooks.models.notebook


def seed():
    Base.metadata.create_all(bind=engine)
