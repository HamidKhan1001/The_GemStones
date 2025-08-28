from pydantic import BaseModel
from typing import Optional

class ItemBase(BaseModel):
    name: str
    description: Optional[str]
    price: float
    image_url: Optional[str]

class ItemCreate(ItemBase):
    ...

class ItemRead(ItemBase):
    id: int
    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    username: str
    password: str

class UserRead(BaseModel):
    id: int
    username: str
    is_admin: bool
    class Config:
        from_attributes = True

class SEOSuggestionRequest(BaseModel):
    name: str
    description: str

class ChatMessage(BaseModel):
    question: str