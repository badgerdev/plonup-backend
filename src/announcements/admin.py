from django.contrib import admin
from django.utils.html import format_html
from django.forms import ValidationError
from django import forms
from django.urls import reverse

from .models import Announcement, AnnouncementImage, AnnouncementLike


# ============================================================
# 🎨 Kolory dla statusów
# ============================================================

USER_STATUS_COLORS = {
    "active": "#22c55e",
    "paused": "#facc15",
    "archived": "#9ca3af",
}

MODERATION_COLORS = {
    "pending": "#a1a1aa",
    "script_check_approved": "#0ea5e9",
    "script_check_rejected": "#f97316",
    "needs_fix": "#eab308",
    "approved": "#16a34a",
    "rejected": "#ef4444",
    "rejected_spam": "#6b7280",
}


# ============================================================
# 🧩 Formularz Admina – JEDYNE MIEJSCE BLOKADY
# ============================================================

class AnnouncementAdminForm(forms.ModelForm):

    class Meta:
        model = Announcement
        fields = "__all__"

    def clean_moderation_status(self):
        new_status = self.cleaned_data.get("moderation_status")
        user = self.instance.user

        # 🔥 Główna walidacja
        if new_status == "approved" and not user.is_verified:
            raise ValidationError(
                "❌ Nie można zatwierdzić ogłoszenia — właściciel konta NIE jest zweryfikowany."
            )

        return new_status


# ============================================================
# 🧩 Inline dla zdjęć i lajków
# ============================================================

class AnnouncementImageInline(admin.TabularInline):
    model = AnnouncementImage
    extra = 0


class AnnouncementLikeInline(admin.TabularInline):
    model = AnnouncementLike
    extra = 0
    readonly_fields = ("user", "created_at")
    can_delete = False


# ============================================================
# 🧩 GŁÓWNY ADMIN OGŁOSZEŃ
# ============================================================

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    form = AnnouncementAdminForm

    list_display = (
        "id",
        "title_link",
        "announcement_type",
        "category",
        "location",
        "user_with_badge",
        "personal_status",
        "moderation_status_colored",
        "created_at",
    )

    list_filter = (
        "announcement_type",
        "category",
        "listing_type",
        "status",
        "moderation_status",
        "created_at",
    )

    search_fields = ("title", "description", "user__username", "category", "location")

    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_select_related = ("user",)
    inlines = [AnnouncementImageInline, AnnouncementLikeInline]
    list_per_page = 25

    readonly_fields = ("visible", "editable", "submission_source", "created_at")

    fieldsets = (
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

    # ----------------------------------------------------------
    # 🔗 Tytuł klikalny
    # ----------------------------------------------------------
    def title_link(self, obj):
        url = reverse("admin:announcements_announcement_change", args=[obj.id])
        return format_html(
            '<a href="{}" style="font-weight:600; color:#2563eb;">{}</a>',
            url,
            obj.title,
        )
    title_link.short_description = "Tytuł"

    # ----------------------------------------------------------
    # 🔗 Użytkownik z badge + link
    # ----------------------------------------------------------
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

    # ----------------------------------------------------------
    # 🟢 Status użytkownika
    # ----------------------------------------------------------
    def personal_status(self, obj):
        color = USER_STATUS_COLORS.get(obj.status, "#9ca3af")
        label = obj.get_status_display_label()
        return format_html(
            '<span style="background:{};color:white;padding:3px 8px;'
            'border-radius:6px;font-size:0.8em;">{}</span>',
            color,
            label,
        )
    personal_status.short_description = "Status użytkownika"

    # ----------------------------------------------------------
    # 🟠 Status moderacji
    # ----------------------------------------------------------
    def moderation_status_colored(self, obj):
        color = MODERATION_COLORS.get(obj.moderation_status, "#9ca3af")
        label = obj.get_moderation_status_display()
        return format_html(
            '<span style="background:{};color:white;padding:3px 8px;'
            'border-radius:6px;font-size:0.8em;">{}</span>',
            color,
            label,
        )
    moderation_status_colored.short_description = "Status moderacji"
