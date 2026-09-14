from pydantic import BaseModel
from typing import List, Optional

class UserBase(BaseModel):
    username: str
    role: str
    roles: Optional[List[str]] = None
    location: str

class UserCreate(UserBase):
    pass

class UserUpdate(UserBase):
    pass

class UserResponse(UserBase):
    id: int
    last_access: str

    class Config:
        from_attributes = True
