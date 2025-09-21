from pydantic import BaseModel
from datetime import datetime

class UserOut(BaseModel):
    id: int
    username: str
    created_at: datetime

    class Config:
        orm_mode = True
