from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db.models import Count
from django.utils.html import mark_safe

from .models import (
    CustomUser,
    Review,
    BlacklistedRefreshToken,
    PasswordResetToken,
)


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser

    list_display = (
        "id",
        "username",
        "email",
        "phone",
        "is_verified",
        "is_staff",
        "is_superuser",
        "is_active",
        "deletion_status",
        "reviews_written_count",
        "reviews_received_count",
    )
    list_display_links = ("username", "email")

    list_filter = (
        "is_staff",
        "is_superuser",
        "is_active",
        "is_verified",
        "is_deleted",
    )

    fieldsets = (
        (None, {"fields": ("id", "username", "password")}),
        ("Dane kontaktowe", {"fields": ("email", "phone")}),
        (
            "Uprawnienia",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Dodatkowe dane", {"fields": ("is_verified",)}),
        ("Ważne daty", {"fields": ("last_login", "date_joined", "last_logout_at")}),
        (
            "Weryfikacja e-mail",
            {
                "classes": ("collapse",),
                "fields": ("email_verification_issued_at", "resend_register_count", "last_register_resend"),
            },
        ),
        (
            "Bezpieczeństwo tokenów",
            {
                "classes": ("collapse",),
                "fields": ("token_version",),
            },
        ),
        (
            "Usuwanie konta",
            {
                "fields": ("is_deleted", "delete_requested_at", "delete_scheduled_for"),
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "phone",
                    "password1",
                    "password2",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )

    readonly_fields = (
        "id",
        "delete_requested_at",
        "delete_scheduled_for",
        "token_version",
        "email_verification_issued_at",
        "last_logout_at",
        "date_joined",
        "last_login",
    )

    search_fields = ("username", "email")
    ordering = ("id",)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(
                _reviews_written=Count("reviews_written", distinct=True),
                _reviews_received=Count("reviews_received", distinct=True),
            )
        )

    def deletion_status(self, obj):
        if obj.is_deleted:
            date_str = (
                obj.delete_scheduled_for.strftime("%d.%m.%Y")
                if obj.delete_scheduled_for
                else "?"
            )
            return mark_safe(
                f'<span style="color:#ef4444;font-weight:600;">🔴 Usunięcie: {date_str}</span>'
            )
        return mark_safe('<span style="color:#16a34a;">🟢 Aktywne</span>')

    deletion_status.short_description = "Status konta"

    def reviews_written_count(self, obj):
        return obj._reviews_written

    def reviews_received_count(self, obj):
        return obj._reviews_received

    reviews_written_count.short_description = "Opinie wystawione"
    reviews_received_count.short_description = "Opinie otrzymane"
    reviews_written_count.admin_order_field = "_reviews_written"
    reviews_received_count.admin_order_field = "_reviews_received"


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "author", "target_user", "rating", "short_comment", "created_at")
    search_fields = ("author__username", "target_user__username", "comment")
    list_filter = ("rating", "created_at")
    ordering = ("-created_at",)
    list_select_related = ("author", "target_user")

    def short_comment(self, obj):
        if not obj.comment:
            return "—"
        return obj.comment[:60] + ("…" if len(obj.comment) > 60 else "")

    short_comment.short_description = "Komentarz"


@admin.register(BlacklistedRefreshToken)
class BlacklistedRefreshTokenAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "short_jti", "revoked_at", "expires_at")
    list_filter = ("revoked_at",)
    search_fields = ("user__username", "jti")
    ordering = ("-revoked_at",)
    list_select_related = ("user",)
    readonly_fields = ("jti", "user", "revoked_at", "expires_at")

    def short_jti(self, obj):
        return obj.jti[:16] + "…"

    short_jti.short_description = "JTI (skrócony)"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "created_at", "expires_at", "is_used")
    list_filter = ("created_at",)
    search_fields = ("user__username",)
    ordering = ("-created_at",)
    list_select_related = ("user",)
    readonly_fields = ("user", "token", "created_at", "expires_at", "used_at")

    def is_used(self, obj):
        if obj.used_at is not None:
            return mark_safe('<span style="color:#16a34a;font-weight:600;">✔ Użyty</span>')
        return mark_safe('<span style="color:#f97316;">✘ Nieużyty</span>')

    is_used.short_description = "Użyty"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
