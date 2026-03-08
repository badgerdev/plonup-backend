# users/account_api.py

from ninja_extra import api_controller, ControllerBase, route
from django.contrib.auth import get_user_model
from django.utils import timezone
from ninja.errors import HttpError


from users.auth_hooks import JWTAuthWithTokenVersion

# MODELE Z INNYCH APLIKACJI
from announcements.models import (
    Announcement,
    AnnouncementImage,
    AnnouncementLike,
)
from users.models import Review
from notifications.models import Notification
from moderation.models import Report

User = get_user_model()


@api_controller("/users", tags=["Account / RODO"])
class AccountController(ControllerBase):
    """
    Lifecycle konta użytkownika:
    - export danych (RODO)
    - delete konta (później)
    """

    @route.get("/me/export", auth=JWTAuthWithTokenVersion())
    def export_my_data(self, request):
        """
        📦 Eksport wszystkich danych użytkownika zgodnie z RODO
        """
        user = request.user

        # =====================================================
        # 👤 USER CORE DATA
        # =====================================================
        user_data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "phone": user.phone,
            "is_verified": user.is_verified,
            "date_joined": user.date_joined,
            "last_login": user.last_login,
            "last_logout_at": user.last_logout_at,
        }

        # =====================================================
        # 📢 ANNOUNCEMENTS
        # =====================================================
        announcements = Announcement.objects.filter(user=user)

        announcements_data = []
        announcement_ids = []

        for a in announcements:
            announcement_ids.append(a.id)

            announcements_data.append({
                "id": a.id,
                "announcement_type": a.announcement_type,
                "title": a.title,
                "description": a.description,
                "category": a.category,
                "location": a.location,
                "postal_code": a.postal_code,
                "listing_type": a.listing_type,
                "email": a.email,
                "phone": a.phone,
                "company_name": a.company_name,
                "address": a.address,
                "opening_hours": a.opening_hours,
                "notes": a.notes,
                "first_name": a.first_name,
                "status": a.status,
                "moderation_status": a.moderation_status,
                "moderation_reason": a.moderation_reason,
                "submission_source": a.submission_source,
                "visible": a.visible,
                "editable": a.editable,
                "created_at": a.created_at,
            })

        # =====================================================
        # 🖼 ANNOUNCEMENT IMAGES
        # =====================================================
        images = AnnouncementImage.objects.filter(
            announcement_id__in=announcement_ids
        )

        images_data = [
            {
                "announcement_id": img.announcement_id,
                "image_url": img.image_url,
                "uploaded_at": img.uploaded_at,
            }
            for img in images
        ]

        # =====================================================
        # ❤️ LIKES (co user polubił)
        # =====================================================
        likes = AnnouncementLike.objects.filter(user=user)

        likes_data = [
            {
                "announcement_id": like.announcement_id,
                "created_at": like.created_at,
            }
            for like in likes
        ]

        # =====================================================
        # ⭐ REVIEWS
        # =====================================================
        reviews_written = Review.objects.filter(author=user)
        reviews_received = Review.objects.filter(target_user=user)

        reviews_written_data = [
            {
                "target_user_id": r.target_user_id,
                "target_username": r.target_user.username,
                "rating": r.rating,
                "comment": r.comment,
                "created_at": r.created_at,
            }
            for r in reviews_written
        ]

        reviews_received_data = [
            {
                "author_user_id": r.author_id,
                "author_username": r.author.username,
                "rating": r.rating,
                "comment": r.comment,
                "created_at": r.created_at,
            }
            for r in reviews_received
        ]

        # =====================================================
        # 🔔 NOTIFICATIONS
        # =====================================================
        notifications = Notification.objects.filter(user=user)

        notifications_data = [
            {
                "title": n.title,
                "message": n.message,
                "type": n.type,
                "link_url": n.link_url,
                "is_read": n.is_read,
                "created_at": n.created_at,
                "related_announcement_id": n.related_announcement_id,
                "created_by": (
                    n.created_by.username if n.created_by else None
                ),
            }
            for n in notifications
        ]

        # =====================================================
        # 🚨 REPORTS (TYLKO ZGŁOSZENIA ZROBIONE PRZEZ USERA)
        # =====================================================
        reports = Report.objects.filter(reported_by=user)

        reports_data = [
            {
                "target_type": r.target_type,
                "target_id": r.target_id,
                "reason": r.reason,
                "category": r.category,
                "status": r.status,
                "created_at": r.created_at,
            }
            for r in reports
        ]

        # =====================================================
        # 📦 FINAL EXPORT
        # =====================================================
        return {
            "user": user_data,
            "announcements": announcements_data,
            "announcement_images": images_data,
            "announcement_likes": likes_data,
            "reviews_written": reviews_written_data,
            "reviews_received": reviews_received_data,
            "notifications": notifications_data,
            "reports_made": reports_data,
            "meta": {
                "exported_at": timezone.now(),
                "format_version": "1.0",
            },
        }

    # Delete acc request
    @route.post("/me/delete-request", auth=JWTAuthWithTokenVersion())
    def request_account_deletion(self, request):
        user = request.user

        if user.is_deleted:
            raise HttpError(400, "Konto jest już zaplanowane do usunięcia.")

        user.schedule_deletion(days=30)
        user.save(update_fields=[
            "is_deleted",
            "delete_requested_at",
            "delete_scheduled_for",
        ])

        return {
            "status": "scheduled",
            "delete_scheduled_for": user.delete_scheduled_for,
        }

    # cancel deleting acc
    @route.post("/me/delete-cancel", auth=JWTAuthWithTokenVersion())
    def cancel_account_deletion(self, request):
        user = request.user

        if not user.is_deleted:
            raise HttpError(400, "Konto nie jest zaplanowane do usunięcia.")

        user.cancel_deletion()
        user.save(update_fields=[
            "is_deleted",
            "delete_requested_at",
            "delete_scheduled_for",
        ])

        return {
            "status": "cancelled",
        }
