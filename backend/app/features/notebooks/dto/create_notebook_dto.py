from pydantic import BaseModel


class CreateNotebookDto(BaseModel):
    title: str
