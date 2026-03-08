from django.db import models
from django.conf import settings

UserModel = settings.AUTH_USER_MODEL


class Notification(models.Model):
    """Powiadomienia systemowe (moderacja, opinie, itp.)"""

    NOTIFICATION_TYPES = [
        ("welcome", "Powitanie"),
        ("moderation", "Moderacja"),
        ("review", "Opinia"),
        ("system", "Systemowe"),
        ("staff_message", "Wiadomość od moderatora"),
    ]

    user = models.ForeignKey(
        UserModel, on_delete=models.CASCADE, related_name="notifications"
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    type = models.CharField(
        max_length=20, choices=NOTIFICATION_TYPES, default="system"
    )
    link_url = models.CharField(max_length=255, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    related_announcement = models.ForeignKey(
        "announcements.Announcement",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="notifications",
    )

    # 🟦 Nowe pola dla ręcznych wiadomości moderatora
    created_by = models.ForeignKey(
        UserModel,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="notifications_sent",
        help_text="Moderator, który utworzył powiadomienie ręcznie.",
    )
    is_staff_message = models.BooleanField(
        default=False,
        help_text="Czy to powiadomienie zostało utworzone ręcznie przez moderatora?",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user}: {self.title}"
