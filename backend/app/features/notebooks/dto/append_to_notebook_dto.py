from pydantic import BaseModel


class AppendToNotebookDto(BaseModel):
    content: str
