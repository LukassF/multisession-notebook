from typing import Optional

from pydantic import BaseModel


class AppendToNotebookDto(BaseModel):
    content: Optional[str] = None
    op: Optional[str] = None
    line_start: Optional[int] = None
    char_start: Optional[int] = None
    text: Optional[str] = None
    length: Optional[int] = None
