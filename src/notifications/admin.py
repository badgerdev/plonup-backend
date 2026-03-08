from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "user",
        "type",
        "is_read",
        "is_staff_message",
        "created_at",
    )
    list_filter = ("type", "is_read", "is_staff_message", "created_at")
    search_fields = ("title", "message", "user__username")

    fieldsets = (
        (None, {
            "fields": ("user", "title", "message", "type", "link_url")
        }),
        ("Zaawansowane", {
            "classes": ("collapse",),
            "fields": (
                "related_announcement",
                "is_read",
                "is_staff_message",
                "created_by",
            ),
        }),
    )

    readonly_fields = ("created_by", "is_staff_message")

    def save_model(self, request, obj, form, change):
        """
        🔧 Ustawia poprawnie typ i flagę zanim zapiszesz obiekt.
        """
        # Jeśli to nowe powiadomienie tworzone w panelu admina
        if not change:
            obj.created_by = request.user
            obj.is_staff_message = True
            obj.type = "staff_message"

        # 🔄 Zabezpieczenie: jeśli moderator zmienił typ ręcznie na staff_message
        # (np. przy edycji istniejącego powiadomienia)
        if obj.type == "staff_message":
            obj.is_staff_message = True
            if not obj.created_by:
                obj.created_by = request.user

        super().save_model(request, obj, form, change)
