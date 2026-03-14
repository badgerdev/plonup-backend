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

ANNOUNCEMENT_FIELDSETS = (
    (
        "Podstawowe",
        {
            "fields": (
                "user",
                "title",
                "description",
                "category",
                "location",
                "postal_code",
                "listing_type",
                "announcement_type",
                "created_at",
            )
        },
    ),
    (
        "Kontakt",
        {
            "fields": ("email", "phone", "first_name"),
        },
    ),
    (
        "Dane firmowe",
        {
            "classes": ("collapse",),
            "fields": ("company_name", "address", "opening_hours", "notes"),
        },
    ),
    (
        "Moderacja",
        {
            "fields": (
                "moderation_status",
                "moderation_reason",
                "submission_source",
            ),
        },
    ),
    (
        "Widoczność",
        {
            "fields": ("status", "visible", "editable"),
        },
    ),
)


# ============================================================
#  BASE ADMIN
# ============================================================

class BaseAnnouncementModerationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title_link",
        "user_with_badge",
        "category",
        "colored_status",
        "created_at",
    )
    list_filter = ("moderation_status", "submission_source", "created_at")
    search_fields = ("title", "description", "user__username")
    ordering = ("-created_at",)
    list_per_page = 25
    list_select_related = ("user",)

    readonly_fields = ("visible", "editable", "submission_source", "created_at")
    fieldsets = ANNOUNCEMENT_FIELDSETS

    # -------------------------------
    # LINK DO OGŁOSZENIA
    # -------------------------------
    def title_link(self, obj):
        url = reverse("admin:announcements_announcement_change", args=[obj.id])
        return format_html(
            '<a href="{}" style="font-weight:600;color:#2563eb;">{}</a>',
            url,
            obj.title,
        )
    title_link.short_description = "Title"

    # -------------------------------
    # STATUS MODERACJI
    # -------------------------------
    def colored_status(self, obj):
        color = STATUS_COLORS.get(obj.moderation_status, "#9ca3af")
        label = obj.get_moderation_status_display()
        return format_html(
            '<span style="background:{};color:white;padding:3px 6px;'
            'border-radius:5px;font-size:0.8em;">{}</span>',
            color,
            label,
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
            '<a href="{}" style="font-weight:600;color:#2563eb;">{}</a>'
            '<span style="margin-left:6px;padding:2px 6px;border-radius:4px;'
            'background:{};color:white;font-size:0.75em;">{}</span>',
            url,
            user.username,
            color,
            label,
        )
    user_with_badge.short_description = "Użytkownik"

    # =======================================================
    # ❌ BLOKADA ZATWIERDZANIA NIEZWERYFIKOWANEGO USERA
    # =======================================================

    def save_model(self, request, obj, form, change):
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
            moderation_status__in=["script_check_approved", "script_check_rejected"]
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
            "review": "#fb9907",
            "user": "#2d8153",
            "announcement": "#1d4ed8",
        }
        border = colors.get(obj.target_type, "#6b7280")
        label = obj.get_target_type_display()
        return format_html(
            '<span style="padding:2px 6px;border:2px solid {};'
            'border-radius:6px;font-size:0.75rem;color:{};'
            'background:white;">{}</span>',
            border,
            border,
            label,
        )
    colored_type.short_description = "Type"

    # ------------------------------------------
    # TARGET → klikalny link do obiektu
    # ------------------------------------------
    def target_link(self, obj):
        try:
            if obj.target_type == "review":
                url = reverse("admin:users_review_change", args=[obj.target_id])
            elif obj.target_type == "announcement":
                url = reverse("admin:announcements_announcement_change", args=[obj.target_id])
            else:
                url = reverse("admin:users_customuser_change", args=[obj.target_id])
        except Exception:
            return format_html(
                '{} #{}',
                obj.get_target_type_display(),
                obj.target_id,
            )

        return format_html(
            '<a href="{}" style="color:#2563eb;font-weight:600;">{} #{}</a>',
            url,
            obj.get_target_type_display(),
            obj.target_id,
        )
    target_link.short_description = "Target"

    # ------------------------------------------
    # CATEGORY → minimalistyczna ramka
    # ------------------------------------------
    def minimal_category(self, obj):
        label = obj.get_category_display()
        return format_html(
            '<span style="padding:2px 6px;border:1px solid #d1d5db;'
            'border-radius:6px;font-size:0.75rem;color:#374151;'
            'background:white;">{}</span>',
            label,
        )
    minimal_category.short_description = "Category"

    # ------------------------------------------
    # STATUS → jedyny kolorowy badge
    # ------------------------------------------
    def colored_status(self, obj):
        colors = {
            "new": "#be4869",
            "in_review": "#666FED",
            "resolved": "#4E4E4E",
        }
        bg = colors.get(obj.status, "#6b7280")
        label = obj.get_status_display()
        return format_html(
            '<span style="background:{};color:white;padding:3px 8px;'
            'border-radius:6px;font-size:0.75rem;">{}</span>',
            bg,
            label,
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
    list_select_related = ("reported_by", "handled_by")

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
