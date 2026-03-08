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

    search_fields = ("title", "description",
                     "user__username", "category", "location")

    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
    inlines = [AnnouncementImageInline, AnnouncementLikeInline]
    list_per_page = 25

    # ----------------------------------------------------------
    # 🔗 Tytuł klikalny
    # ----------------------------------------------------------
    def title_link(self, obj):
        url = f"/admin/announcements/announcement/{obj.id}/change/"
        return format_html(
            f'<a href="{url}" style="font-weight:600; color:#2563eb;">{obj.title}</a>'
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
            f'<a href="{url}" style="font-weight:600;color:#2563eb;">{user.username}</a>'
            f'<span style="margin-left:6px;padding:2px 6px;border-radius:4px;'
            f'background:{color};color:white;font-size:0.75em;">{label}</span>'
        )
    user_with_badge.short_description = "Użytkownik"

    # ----------------------------------------------------------
    # 🟢 Status użytkownika
    # ----------------------------------------------------------
    def personal_status(self, obj):
        color = USER_STATUS_COLORS.get(obj.status, "#9ca3af")
        label = obj.get_status_display_label()
        return format_html(
            f'<span style="background:{color};color:white;padding:3px 8px;'
            f'border-radius:6px;font-size:0.8em;">{label}</span>'
        )
    personal_status.short_description = "Status użytkownika"

    # ----------------------------------------------------------
    # 🟠 Status moderacji
    # ----------------------------------------------------------
    def moderation_status_colored(self, obj):
        color = MODERATION_COLORS.get(obj.moderation_status, "#9ca3af")
        label = obj.get_moderation_status_display()
        return format_html(
            f'<span style="background:{color};color:white;padding:3px 8px;'
            f'border-radius:6px;font-size:0.8em;">{label}</span>'
        )
    moderation_status_colored.short_description = "Status moderacji"
