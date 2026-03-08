from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from announcements.constants import ModerationStatusType


# ============================================================
# 🧩 Report Schemas (input / output)
# ============================================================

class ReportInSchema(BaseModel):
    """Schema for creating a new user report."""

    target_type: str = Field(
        ...,
        description="Type of reported object (announcement, review, user)",
        examples=["announcement", "review", "user"],
    )
    target_id: int = Field(
        ..., description="ID of the reported object", example=42
    )
    category: str = Field(
        ...,
        description="Report category",
        examples=["spam", "offensive",
                  "rules_violation", "inappropriate", "other"],
    )
    reason: str = Field(
        ..., description="Reason for the report", example="This listing contains external links."
    )


class ReportOutSchema(BaseModel):
    """Schema for returning report data to moderators."""

    id: int
    target_type: str
    target_id: int
    reported_by: str
    category: str
    reason: str
    status: str
    handled_reason: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# 🧩 Moderation - Announcements overview
# ============================================================

class ModerationAnnouncementOut(BaseModel):
    """Schema for announcements visible in moderation dashboard."""

    id: int
    title: str
    user: str
    created_at: datetime
    status: str
    moderation_status: ModerationStatusType  # comes from constants.py
