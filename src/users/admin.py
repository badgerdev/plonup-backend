from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Review


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
        "reviews_written_count",
        "reviews_received_count",
    )
    list_display_links = ("username", "email")

    list_filter = ("is_staff", "is_superuser", "is_active", "is_verified")

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
        ("Ważne daty", {"fields": ("last_login", "date_joined")}),
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

    readonly_fields = ("id",)

    search_fields = ("username", "email")
    ordering = ("id",)

    # helpery do policzenia opinii
    def reviews_written_count(self, obj):
        return obj.reviews_written.count()

    def reviews_received_count(self, obj):
        return obj.reviews_received.count()

    reviews_written_count.short_description = "Opinie wystawione"
    reviews_received_count.short_description = "Opinie otrzymane"


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "author", "target_user",
                    "rating", "comment", "created_at")
    search_fields = ("author__username", "target_user__username", "comment")
    list_filter = ("rating", "created_at")
    ordering = ("-created_at",)
