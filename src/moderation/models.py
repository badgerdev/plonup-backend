from django.db import models
from django.conf import settings
from announcements.models import Announcement

UserModel = settings.AUTH_USER_MODEL


# ============================================================
# 🧩 Proxy modele dla moderacji (każdy odpowiada jednej sekcji)
# ============================================================

class AnnouncementChecked(Announcement):
    """Ogłoszenia sprawdzone automatycznie przez MilfCheckera."""
    class Meta:
        proxy = True
        verbose_name = "Nowe (sprawdzone przez MilfCheckera)"
        verbose_name_plural = "Nowe (sprawdzone przez MilfCheckera)"


class AnnouncementPendingEdit(Announcement):
    """Ogłoszenia oczekujące po edycji użytkownika."""
    class Meta:
        proxy = True
        verbose_name = "Oczekujące po edycji"
        verbose_name_plural = "Oczekujące po edycji"


class AnnouncementResubmitted(Announcement):
    """Poprawione po odrzuceniu przez użytkownika."""
    class Meta:
        proxy = True
        verbose_name = "Poprawione po odrzuceniu"
        verbose_name_plural = "Poprawione po odrzuceniu"


class AnnouncementNeedsFix(Announcement):
    """Wymagające poprawek od użytkownika."""
    class Meta:
        proxy = True
        verbose_name = "Do poprawy"
        verbose_name_plural = "Do poprawy"


class AnnouncementRejected(Announcement):
    """Odrzucone przez moderatora."""
    class Meta:
        proxy = True
        verbose_name = "Odrzucone przez moderatora"
        verbose_name_plural = "Odrzucone przez moderatora"


class AnnouncementSpam(Announcement):
    """Zablokowane / spam."""
    class Meta:
        proxy = True
        verbose_name = "Spam / zablokowane"
        verbose_name_plural = "Spam / zablokowane"


# ============================================================
# 🚨 Zgłoszenia – uniwersalny model (użytkownik / opinia / ogłoszenie)
# ============================================================

class Report(models.Model):
    TARGET_TYPES = [
        ("announcement", "Announcement"),
        ("review", "Review"),
        ("user", "User"),
    ]

    STATUS_CHOICES = [
        ("new", "New"),
        ("in_review", "In review"),
        ("resolved", "Resolved"),
    ]

    CATEGORY_CHOICES = [
        ("spam", "Spam / Advertising"),
        ("offensive", "Offensive content"),
        ("rules_violation", "Rules violation"),
        ("inappropriate", "Inappropriate behaviour"),
        ("other", "Other"),
    ]

    target_type = models.CharField(max_length=20, choices=TARGET_TYPES)
    target_id = models.PositiveIntegerField()
    reported_by = models.ForeignKey(
        UserModel, on_delete=models.CASCADE, related_name="reports_made"
    )
    reason = models.TextField(max_length=300)
    category = models.CharField(
        max_length=30, choices=CATEGORY_CHOICES, default="other", db_index=True
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="new", db_index=True
    )

    handled_by = models.ForeignKey(
        UserModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports_handled",
    )
    handled_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Report"
        verbose_name_plural = "Reports"

    def __str__(self):
        return f"{self.get_target_type_display()} #{self.target_id} ({self.status})"
