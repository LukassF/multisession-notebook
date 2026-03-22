from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.sql import func
from app.core.database.index import Base


class Notebook(Base):
    __tablename__ = "notebooks"

    id = Column(String, primary_key=True)
    title = Column(String)
    content = Column(String)  # link to the file in storage
    admin_id = Column(Integer)  # user id of the notebook owner
    collaborators = Column(
        JSON, default=list
    )  # list of user ids who have access to the notebook (besides the admin)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "admin_id": self.admin_id,
            "collaborators": self.collaborators,
            "created_at": self.created_at.isoformat(),
        }
