from ninja_extra import api_controller, route, ControllerBase
from ninja_jwt.authentication import JWTAuth
from django.shortcuts import get_object_or_404
from typing import List

from utils.ensure_account_not_pending_deletion import (
    ensure_account_not_pending_deletion,
)


from users.auth_hooks import JWTAuthWithTokenVersion
from .models import Notification
from .schemas import NotificationOutSchema


@api_controller("/notifications", tags=["notifications"], auth=JWTAuthWithTokenVersion())
class NotificationController(ControllerBase):
    """Obsługa powiadomień użytkownika"""

    @route.get("/", response=List[NotificationOutSchema])
    def list_user_notifications(self):
        user = self.context.request.user
        return Notification.objects.filter(user=user).order_by("-created_at")

    @route.patch("/{notification_id}/read", response={200: dict})
    def mark_as_read(self, notification_id: int):

        user = self.context.request.user

        notif = get_object_or_404(Notification, id=notification_id, user=user)
        notif.is_read = True
        notif.save()
        return {"success": True}

    @route.patch("/mark-all-read", response={200: dict})
    def mark_all_read(self):
        user = self.context.request.user

        Notification.objects.filter(
            user=user, is_read=False).update(is_read=True)
        return {"success": True, "message": "Wszystkie powiadomienia oznaczono jako przeczytane."}

# DELETE
    @route.delete("/{notification_id}", response={200: dict})
    def delete_notification(self, notification_id: int):
        user = self.context.request.user
        ensure_account_not_pending_deletion(user)

        notif = get_object_or_404(Notification, id=notification_id, user=user)
        notif.delete()
        return {"success": True, "message": "Powiadomienie usunięte."}
