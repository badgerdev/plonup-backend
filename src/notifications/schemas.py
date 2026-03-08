from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class NotificationOutSchema(BaseModel):
    id: int
    title: str
    message: str
    type: str
    link_url: Optional[str] = None
    is_read: bool
    created_at: datetime
    related_announcement_id: Optional[int] = None

    class Config:
        from_attributes = True
