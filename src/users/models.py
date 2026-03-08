from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta


class CustomUser(AbstractUser):
    phone = models.CharField(max_length=20, blank=True)
    is_verified = models.BooleanField(default=False)
    last_logout_at = models.DateTimeField(null=True, blank=True)
    token_version = models.PositiveIntegerField(default=1)

    email_verification_issued_at = models.DateTimeField(
        null=True, blank=True
    )

    resend_register_count = models.PositiveIntegerField(default=0)

    last_register_resend = models.DateTimeField(null=True, blank=True)

    # SOFT DELETE / HIBERNATION
    is_deleted = models.BooleanField(default=False)
    delete_requested_at = models.DateTimeField(null=True, blank=True)
    delete_scheduled_for = models.DateTimeField(null=True, blank=True)

    def schedule_deletion(self, days: int = 30):
        now = timezone.now()
        self.is_deleted = True
        self.delete_requested_at = now
        self.delete_scheduled_for = now + timedelta(days=days)

    def cancel_deletion(self):
        self.is_deleted = False
        self.delete_requested_at = None
        self.delete_scheduled_for = None

    def __str__(self):
        return self.username


class Review(models.Model):
    author = models.ForeignKey(
        CustomUser, related_name="reviews_written", on_delete=models.CASCADE
    )
    target_user = models.ForeignKey(
        CustomUser, related_name="reviews_received", on_delete=models.CASCADE
    )
    rating = models.PositiveSmallIntegerField()  # 1–5
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("author", "target_user")  # 1 ocena na użytkownika

    def __str__(self):
        return f"{self.author} → {self.target_user} ({self.rating})"


class BlacklistedRefreshToken(models.Model):
    """
    Przechowuje unieważnione refresh tokeny (po jti).
    """

    jti = models.CharField(max_length=255, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="blacklisted_refresh_tokens",
    )
    revoked_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()

    def __str__(self):
        return f"Blacklisted jti={self.jti} user={self.user_id}"


class PasswordResetToken(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens",
    )
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    def is_valid(self):
        return self.used_at is None and timezone.now() < self.expires_at
