# announcements/schemas.py
from pydantic import BaseModel, EmailStr, Field, model_validator, model_serializer
from typing import Literal, Optional, Union, List
from datetime import datetime

from .constants import ListingType, AnnouncementType, StatusType, ModerationStatusType


# ---------------------------------------
# BASE SCHEMAS
# ---------------------------------------
class BaseAnnouncementSchema(BaseModel):
    title: str
    description: str
    category: str
    location: str
    postal_code: Optional[str] = Field(None, alias="postalCode")
    listing_type: ListingType
    email: Optional[EmailStr] = None
    phone: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def at_least_one_contact(cls, data):
        """Ensure that at least one contact method is provided."""
        if not data.get("email") and not data.get("phone"):
            raise ValueError("Musisz podać e-mail lub numer telefonu.")
        return data

    @model_serializer(mode="wrap")
    def serialize(self, info):
        """Common serialized output for shared fields."""
        return {
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "location": self.location,
            "postal_code": self.postal_code,
            "listing_type": self.listing_type,
            "email": self.email,
            "phone": self.phone,
        }


# ---------------------------------------
# CREATE SCHEMAS
# ---------------------------------------
class AnnouncementPrivateSchema(BaseAnnouncementSchema):
    announcement_type: Literal["private"]
    first_name: str

    @model_serializer(mode="wrap")
    def serialize(self, info):
        data = super().serialize()
        data.update({
            "announcement_type": "private",
            "first_name": self.first_name,
        })
        return data


class AnnouncementBusinessSchema(BaseAnnouncementSchema):
    announcement_type: Literal["business"]
    company_name: str
    address: str
    opening_hours: str
    notes: Optional[str] = None

    @model_serializer(mode="wrap")
    def serialize(self, info):
        data = super().serialize()
        data.update({
            "announcement_type": "business",
            "company_name": self.company_name,
            "address": self.address,
            "opening_hours": self.opening_hours,
            "notes": self.notes,
        })
        return data


AnnouncementCreateSchema = Union[AnnouncementPrivateSchema,
                                 AnnouncementBusinessSchema]


class AnnouncementCreateWithImagesSchema(BaseModel):
    announcement_type: AnnouncementType
    title: str
    description: str
    category: str
    location: str
    postal_code: Optional[str] = None
    listing_type: ListingType
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    first_name: Optional[str] = None
    company_name: Optional[str] = None
    address: Optional[str] = None
    opening_hours: Optional[str] = None
    notes: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def at_least_one_contact(cls, data):
        if not data.get("email") and not data.get("phone"):
            raise ValueError("Musisz podać e-mail lub numer telefonu.")
        return data


# ---------------------------------------
# OUT SCHEMAS
# ---------------------------------------
class AnnouncementImageOutSchema(BaseModel):
    id: int
    image_url: str


class AnnouncementOutSchema(BaseModel):
    id: int
    title: str
    category: str
    location: str
    listing_type: str
    announcement_type: str
    status: str
    moderation_status: ModerationStatusType  # ✅ nowy typ
    status_display: str
    created_at: datetime
    images: List[AnnouncementImageOutSchema] = []
    user: str
    user_id: int
    likes_count: int
    is_liked: bool = False

    class Config:
        from_attributes = True


class AnnouncementDetailSchema(BaseModel):
    id: int
    user_id: int
    user: str
    is_owner: bool = False
    title: str
    description: str
    category: str
    location: str
    postal_code: Optional[str]
    listing_type: str
    email: Optional[str]
    phone: Optional[str]
    announcement_type: str
    first_name: Optional[str]
    company_name: Optional[str]
    address: Optional[str]
    opening_hours: Optional[str]
    notes: Optional[str]
    status: str
    moderation_status: ModerationStatusType  # ✅ dodane
    status_display: str
    created_at: datetime
    images: List[AnnouncementImageOutSchema] = []
    likes_count: int
    is_liked: bool = False

    class Config:
        from_attributes = True


class StatusUpdateSchema(BaseModel):
    status: StatusType


class AnnouncementEditSchema(BaseModel):
    title: str
    description: str
    category: str
    location: str
    postal_code: Optional[str] = ""
    listing_type: ListingType
    email: Optional[str] = ""
    phone: Optional[str] = ""
    first_name: Optional[str] = ""
    company_name: Optional[str] = ""
    address: Optional[str] = ""
    opening_hours: Optional[str] = ""
    notes: Optional[str] = ""
