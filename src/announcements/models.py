from django.db import models
from django.conf import settings
from .constants import (
    LISTING_TYPE_CHOICES,
    ANNOUNCEMENT_TYPE_CHOICES,
    STATUS_CHOICES,
    MODERATION_STATUS_CHOICES,
    SUBMISSION_SOURCE_CHOICES,
)

UserModel = settings.AUTH_USER_MODEL


class Announcement(models.Model):
    """Podstawowy model ogłoszenia."""
    user = models.ForeignKey(
        UserModel, on_delete=models.CASCADE, related_name="announcements"
    )
    announcement_type = models.CharField(
        max_length=10, choices=ANNOUNCEMENT_TYPE_CHOICES)
    title = models.CharField(max_length=120)
    description = models.TextField(max_length=500)
    category = models.CharField(max_length=50)
    location = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, blank=True)
    listing_type = models.CharField(
        max_length=22, choices=LISTING_TYPE_CHOICES)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)

    # Pola specyficzne dla prywatnych / firmowych
    company_name = models.CharField(max_length=100, blank=True)
    address = models.CharField(max_length=200, blank=True)
    opening_hours = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    first_name = models.CharField(max_length=50, blank=True)

    # Status / moderacja
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="active")
    moderation_status = models.CharField(
        max_length=25, choices=MODERATION_STATUS_CHOICES, default="pending", db_index=True
    )
    moderation_reason = models.TextField(blank=True)

    # Workflow
    submission_source = models.CharField(
        max_length=20, choices=SUBMISSION_SOURCE_CHOICES, default="new", db_index=True
    )

    visible = models.BooleanField(default=False)
    editable = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["moderation_status"]),
            models.Index(fields=["submission_source"]),
        ]

    def get_status_display_label(self):
        return dict(STATUS_CHOICES).get(self.status, self.status)

    def is_public(self):
        return self.status == "active" and self.moderation_status == "approved"

    def __str__(self):
        return f"{self.title} ({self.announcement_type})"


class AnnouncementImage(models.Model):
    announcement = models.ForeignKey(
        Announcement, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="announcement_images/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    @property
    def image_url(self):
        return self.image.url if self.image else ""


class AnnouncementLike(models.Model):
    announcement = models.ForeignKey(
        Announcement, on_delete=models.CASCADE, related_name="likes"
    )
    user = models.ForeignKey(
        UserModel, on_delete=models.CASCADE, related_name="announcement_likes"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["announcement", "user"], name="unique_announcement_like"
            )
        ]

    def __str__(self):
        return f"Like: {self.user_id} -> {self.announcement_id}"
