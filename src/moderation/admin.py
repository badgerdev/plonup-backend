from django.contrib import admin
from django.utils.html import format_html
from django.core.exceptions import ValidationError
from django.urls import reverse

from .models import (
    AnnouncementChecked,
    AnnouncementPendingEdit,
    AnnouncementResubmitted,
    AnnouncementNeedsFix,
    AnnouncementRejected,
    AnnouncementSpam,
    Report,
)

STATUS_COLORS = {
    "pending": "#a1a1aa",
    "script_check_approved": "#0ea5e9",
    "script_check_rejected": "#f97316",
    "needs_fix": "#eab308",
    "approved": "#16a34a",
    "rejected": "#ef4444",
    "rejected_spam": "#6b7280",
}


# ============================================================
#  BASE ADMIN
# ============================================================

class BaseAnnouncementModerationAdmin(admin.ModelAdmin):
    list_display = ("id", "title_link", "user_with_badge",
                    "category", "colored_status", "created_at")
    search_fields = ("title", "description", "user__username")
    ordering = ("-created_at",)
    list_per_page = 25

    # -------------------------------
    # LINK DO OGŁOSZENIA
    # -------------------------------
    def title_link(self, obj):
        url = f"/admin/announcements/announcement/{obj.id}/change/"
        return format_html(
            f'<a href="{url}" style="font-weight:600;color:#2563eb;">{obj.title}</a>'
        )
    title_link.short_description = "Title"

    # -------------------------------
    # STATUS MODERACJI
    # -------------------------------
    def colored_status(self, obj):
        color = STATUS_COLORS.get(obj.moderation_status, "#9ca3af")
        label = obj.get_moderation_status_display()
        return format_html(
            f'<span style="background:{color};color:white;padding:3px 6px;'
            f'border-radius:5px;font-size:0.8em;">{label}</span>'
        )
    colored_status.short_description = "Moderation status"

    # -------------------------------
    # USER + BADGE + LINK
    # -------------------------------
    def user_with_badge(self, obj):
        user = obj.user
        color = "#16a34a" if user.is_verified else "#ef4444"
        label = "Zweryfikowany" if user.is_verified else "Niezweryfikowany"

        url = reverse("admin:users_customuser_change", args=[user.id])

        return format_html(
            f'<a href="{url}" style="font-weight:600;color:#2563eb;">{user.username}</a>'
            f'<span style="margin-left:6px;padding:2px 6px;border-radius:4px;'
            f'background:{color};color:white;font-size:0.75em;">{label}</span>'
        )
    user_with_badge.short_description = "Użytkownik"

    # =======================================================
    # ❌ BLOKADA ZATWIERDZANIA NIEZWERYFIKOWANEGO USERA
    # =======================================================

    def save_model(self, request, obj, form, change):
        """
        Blokuje zapis, jeśli moderator próbuje ustawić "approved",
        a użytkownik NIE jest zweryfikowany.
        """

        new_status = form.cleaned_data.get("moderation_status", None)

        if new_status == "approved" and not obj.user.is_verified:
            raise ValidationError(
                "❌ Nie można zatwierdzić ogłoszenia – właściciel konta NIE zweryfikował adresu e-mail."
            )

        super().save_model(request, obj, form, change)


# ============================================================
#  SEKCJE MODERACJI
# ============================================================

@admin.register(AnnouncementChecked)
class AnnouncementCheckedAdmin(BaseAnnouncementModerationAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(
            moderation_status__in=[
                "script_check_approved", "script_check_rejected"]
        )


@admin.register(AnnouncementPendingEdit)
class AnnouncementPendingEditAdmin(BaseAnnouncementModerationAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(
            submission_source="edited", moderation_status="pending"
        )


@admin.register(AnnouncementResubmitted)
class AnnouncementResubmittedAdmin(BaseAnnouncementModerationAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(
            submission_source="resubmitted", moderation_status="pending"
        )


@admin.register(AnnouncementNeedsFix)
class AnnouncementNeedsFixAdmin(BaseAnnouncementModerationAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(moderation_status="needs_fix")


@admin.register(AnnouncementRejected)
class AnnouncementRejectedAdmin(BaseAnnouncementModerationAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(moderation_status="rejected")


@admin.register(AnnouncementSpam)
class AnnouncementSpamAdmin(BaseAnnouncementModerationAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(moderation_status="rejected_spam")


# ============================================================
#  REPORTS ADMIN
# ============================================================

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):

    # ------------------------------------------
    # CUSTOM BADGE — TYPE (minimal outline)
    # ------------------------------------------
    def colored_type(self, obj):
        colors = {
            "review": "#fb9907",        # purple
            "user": "#2d8153",          # teal
            "announcement": "#1d4ed8",  # blue
        }
        border = colors.get(obj.target_type, "#6b7280")
        label = obj.get_target_type_display()

        return format_html(
            f'<span style="padding:2px 6px;border:2px solid {border};'
            f'border-radius:6px;font-size:0.75rem;color:{border};'
            f'background:white;">{label}</span>'
        )
    colored_type.short_description = "Type"

    # ------------------------------------------
    # TARGET → klikalny link do obiektu
    # ------------------------------------------
    def target_link(self, obj):
        if obj.target_type == "review":
            url = f"/admin/users/review/{obj.target_id}/change/"
        elif obj.target_type == "announcement":
            url = f"/admin/announcements/announcement/{obj.target_id}/change/"
        else:
            url = f"/admin/users/customuser/{obj.target_id}/change/"

        return format_html(
            f'<a href="{url}" style="color:#2563eb;font-weight:600;">'
            f'{obj.get_target_type_display()} #{obj.target_id}</a>'
        )
    target_link.short_description = "Target"

    # ------------------------------------------
    # CATEGORY → minimalistyczna ramka
    # ------------------------------------------
    def minimal_category(self, obj):
        label = obj.get_category_display()
        return format_html(
            f'<span style="padding:2px 6px;border:1px solid #d1d5db;'
            f'border-radius:6px;font-size:0.75rem;color:#374151;'
            f'background:white;">{label}</span>'
        )
    minimal_category.short_description = "Category"

    # ------------------------------------------
    # STATUS → jedyny kolorowy badge
    # ------------------------------------------
    def colored_status(self, obj):
        colors = {
            "new": "#be4869",        # yellow
            "in_review": "#666FED",  # blue
            "resolved": "#4E4E4E",   # green
        }
        bg = colors.get(obj.status, "#6b7280")
        label = obj.get_status_display()

        return format_html(
            f'<span style="background:{bg};color:white;padding:3px 8px;'
            f'border-radius:6px;font-size:0.75rem;">{label}</span>'
        )
    colored_status.short_description = "Status"

    # ------------------------------------------
    # LIST DISPLAY
    # ------------------------------------------
    list_display = (
        "id",
        "colored_type",
        "target_link",
        "minimal_category",
        "reported_by",
        "colored_status",
        "created_at",
        "handled_by",
    )

    list_filter = ("target_type", "category", "status")
    search_fields = ("reason", "reported_by__username", "handled_reason")
    ordering = ("-created_at",)

    readonly_fields = ("created_at",)

    fieldsets = (
        (None, {
            "fields": ("target_type", "target_id", "category", "reason")
        }),
        ("Reporter", {
            "fields": ("reported_by",)
        }),
        ("Status", {
            "fields": ("status", "handled_by", "handled_reason")
        }),
        ("Timestamps", {
            "fields": ("created_at",)
        }),
    )
