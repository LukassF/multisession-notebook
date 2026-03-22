from pydantic import BaseModel


class InviteToNotebookDto(BaseModel):
    emails: list[str]
