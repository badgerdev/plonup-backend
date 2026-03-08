from django.shortcuts import get_object_or_404
from ninja_extra import api_controller, route, ControllerBase
from ninja_jwt.authentication import JWTAuth
from ninja.errors import HttpError
from typing import List

from moderation.schemas import (
    ModerationAnnouncementOut,
    ReportInSchema,
    ReportOutSchema,
)
from users.auth_hooks import JWTAuthWithTokenVersion
from utils.is_user_verified import ensure_user_verified
from utils.ensure_account_not_pending_deletion import (
    ensure_account_not_pending_deletion,
)


from .models import Report
from announcements.models import Announcement
from notifications.models import Notification
from users.models import CustomUser, Review  # Review = model opinii

# ✅ import stałych z announcements/constants.py
from announcements.constants import MODERATION_STATUS_CHOICES
MOD_STATUS = {c[0]: c[1] for c in MODERATION_STATUS_CHOICES}

PENDING = "pending"
SCRIPT_APPROVED = "script_check_approved"
SCRIPT_REJECTED = "script_check_rejected"
APPROVED = "approved"
REJECTED = "rejected"
NEEDS_FIX = "needs_fix"
REJECTED_SPAM = "rejected_spam"


# ============================================================
# 🧩 Walidacja celu zgłoszenia
# ============================================================

def validate_target(target_type: str, target_id: int):
    model_map = {
        "announcement": Announcement,
        "review": Review,
        "user": CustomUser,
    }
    model = model_map.get(target_type)
    if not model:
        raise HttpError(400, "Nieprawidłowy typ zgłoszenia.")
    obj = model.objects.filter(id=target_id).first()
    if not obj:
        raise HttpError(
            404, f"{target_type.capitalize()} o ID {target_id} nie istnieje.")
    return obj


# ============================================================
# 🛡️ Główny kontroler moderacji + zgłoszeń
# ============================================================

@api_controller("/moderation", tags=["moderation"], auth=JWTAuthWithTokenVersion())
class ModerationController(ControllerBase):
    """Moderacja + obsługa zgłoszeń."""

    # -----------------------------------------
    # 🚨 NOWE ZGŁOSZENIA
    # -----------------------------------------
    @route.post("/reports", response={201: dict})
    def create_report(self, request, data: ReportInSchema):
        """Creates a new report (for logged-in user)."""
        user = request.user
        ensure_account_not_pending_deletion(user)
        ensure_user_verified(user)

        target = validate_target(data.target_type, data.target_id)

        # 🚫 Prevent self-reporting
        if data.target_type == "user" and data.target_id == user.id:
            raise HttpError(400, "Nie możesz zgłosić samego siebie.")

       # 🚫 Prevent duplicate reports from the same user
        existing = Report.objects.filter(
            target_type=data.target_type,
            target_id=data.target_id,
            reported_by=user,
        ).first()

        if existing:
            raise HttpError(400, "Już wysłałeś takie zgłoszenie...")

        # ✅ Create new report
        report = Report.objects.create(
            target_type=data.target_type,
            target_id=data.target_id,
            category=data.category,
            reason=data.reason,
            reported_by=user,
        )

        return {
            "message": f"Report #{report.id} has been submitted to the moderation team.",
            "id": report.id,
            "category": report.category,
        }

    @route.get("/reports", response=List[ReportOutSchema])
    def list_reports(self, request):
        """Lista wszystkich zgłoszeń (tylko staff)."""
        if not request.user.is_staff:
            raise HttpError(403, "Brak uprawnień.")

        reports = Report.objects.select_related("reported_by").all()
        return [
            {
                "id": r.id,
                "target_type": r.target_type,
                "target_id": r.target_id,
                "reported_by": r.reported_by.username,
                "reason": r.reason,
                "created_at": r.created_at,
                "handled": r.handled,
                "handled_by": r.handled_by.username if r.handled_by else None,
                "handled_reason": r.handled_reason,
            }
            for r in reports
        ]

    # -----------------------------------------
    # 🧩 ISTNIEJĄCA CZĘŚĆ MODERACJI OGŁOSZEŃ
    # -----------------------------------------

    @route.get("/pending", response=List[ModerationAnnouncementOut])
    def list_pending(self, request):
        """Lista ogłoszeń oczekujących na moderację."""
        if not request.user.is_staff:
            raise HttpError(403, "Brak uprawnień")

        anns = Announcement.objects.filter(
            moderation_status=PENDING).select_related("user")

        return [
            ModerationAnnouncementOut.model_validate(
                {
                    "id": a.id,
                    "title": a.title,
                    "user": a.user.username,
                    "created_at": a.created_at,
                    "status": a.status,
                    "moderation_status": a.moderation_status,
                }
            )
            for a in anns
        ]

    @route.post("/{announcement_id}/approve", auth=JWTAuthWithTokenVersion())
    def approve(self, request, announcement_id: int):
        """Zatwierdź ogłoszenie."""
        if not request.user.is_staff:
            raise HttpError(403, "Brak uprawnień")

        ann = get_object_or_404(Announcement, id=announcement_id)

        # BEZ printów w produkcji, ale można dodać logger
        # print("User verified:", ann.user.is_verified)

        if not ann.user.is_verified:
            raise HttpError(
                400,
                "Nie możesz zatwierdzić ogłoszenia – właściciel konta nie zweryfikował adresu e-mail."
            )

        ann.moderation_status = "approved"
        ann.moderation_reason = ""
        ann.visible = True
        ann.editable = False
        ann.save()

        Notification.objects.create(
            user=ann.user,
            title="Ogłoszenie zatwierdzone",
            message=f"Twoje ogłoszenie „{ann.title}” zostało zaakceptowane i jest już widoczne publicznie.",
            related_announcement=ann,
        )

        return {"message": f"Ogłoszenie {ann.id} zostało zatwierdzone."}

    @route.post("/{announcement_id}/reject", auth=JWTAuthWithTokenVersion())
    def reject(self, request, announcement_id: int, reason: str = "Odrzucone przez moderatora"):
        """Odrzuć ogłoszenie z powodem."""
        if not request.user.is_staff:
            raise HttpError(403, "Brak uprawnień")

        ann = get_object_or_404(Announcement, id=announcement_id)
        ann.moderation_status = REJECTED
        ann.moderation_reason = reason
        ann.visible = False
        ann.editable = True
        ann.save()

        Notification.objects.create(
            user=ann.user,
            title="Ogłoszenie odrzucone",
            message=f"Twoje ogłoszenie „{ann.title}” zostało odrzucone przez moderatora. Powód: {reason}",
            related_announcement=ann,
        )

        return {"message": f"Ogłoszenie {ann.id} zostało odrzucone. Powód: {reason}"}
