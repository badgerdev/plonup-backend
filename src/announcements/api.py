
from django.db.models import (
    Q,
    Case,
    When,
    IntegerField,
    Count,
    Exists,
    OuterRef,
)
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from users.auth_hooks import JWTAuthWithTokenVersion


from announcements.utils.auth_helpers import get_user_from_request

from ninja_extra import api_controller, route, ControllerBase
from ninja import File, UploadedFile, Form, Query, Path, Body
from typing import List, Optional
from ninja.responses import Response
from ninja.errors import HttpError

# 💋 MilfChecker – automatyczna weryfikacja treści
from announcements.utils.milfchecker import milfchecker
# weryfikacja maila
from utils.is_user_verified import ensure_user_verified
from utils.ensure_account_not_pending_deletion import (
    ensure_account_not_pending_deletion,
)


from announcements.geocoding import geocode_city, haversine
from announcements.schemas import (
    AnnouncementCreateWithImagesSchema,
    AnnouncementOutSchema,
    AnnouncementDetailSchema,
    StatusUpdateSchema,
    AnnouncementEditSchema,
)
from announcements.models import Announcement, AnnouncementImage, AnnouncementLike
from notifications.models import Notification


# CONSTANTS
from announcements.constants import STATUS_CHOICES, MODERATION_STATUS_CHOICES
MOD_STATUS = {c[0]: c[1] for c in MODERATION_STATUS_CHOICES}

PENDING = "pending"
SCRIPT_APPROVED = "script_check_approved"
SCRIPT_REJECTED = "script_check_rejected"
APPROVED = "approved"
REJECTED = "rejected"
NEEDS_FIX = "needs_fix"
REJECTED_SPAM = "rejected_spam"

VALID_CATEGORIES = [
    "owoce", "warzywa", "mięso", "nabiał", "przetwory", "słoiki", "jaja",
    "miód", "zboża", "zioła", "oleje", "pieczywo", "napoje", "inne"
]


@api_controller("/announcements", tags=["announcements"], auth=JWTAuthWithTokenVersion())
class AnnouncementController(ControllerBase):
    @route.post("/", auth=JWTAuthWithTokenVersion())
    def create_announcement(
        self,
        data: AnnouncementCreateWithImagesSchema = Form(...),
        images: List[UploadedFile] = File(default=[]),
    ):
        user = self.context.request.user
        ensure_account_not_pending_deletion(user)

        # 🔎 MilfChecker – automatyczna weryfikacja
        moderation_status, moderation_reason = milfchecker(
            data.title, data.description
        )

        # 🔧 wspólne pola ogłoszenia
        common_fields = dict(
            user=user,
            announcement_type=data.announcement_type,
            title=data.title,
            description=data.description,
            category=data.category,
            location=data.location,
            postal_code=data.postal_code or "",
            listing_type=data.listing_type,
            email=data.email or "",
            phone=data.phone or "",
            moderation_status=moderation_status,
            moderation_reason=moderation_reason,
            visible=False,
            editable=False,
        )

        # 🧱 tworzymy obiekt zależnie od typu
        if data.announcement_type == "private":
            ann = Announcement.objects.create(
                **common_fields,
                first_name=data.first_name or "",
            )
        else:
            ann = Announcement.objects.create(
                **common_fields,
                company_name=data.company_name or "",
                address=data.address or "",
                opening_hours=data.opening_hours or "",
                notes=data.notes or "",
            )

        # 📸 zapis zdjęć (max 3)
        for img in images[:3]:
            AnnouncementImage.objects.create(announcement=ann, image=img)

        # 🔔 tworzymy powiadomienie dla użytkownika
        if moderation_status == "script_check_rejected":
            msg = f"Ogłoszenie zostało odrzucone automatycznie. Powód: {moderation_reason}"
        else:
            msg = "Twoje ogłoszenie zostało przesłane do moderacji i czeka na weryfikację moderatora."

        Notification.objects.create(
            user=user,
            title="Dodano ogłoszenie",
            message=msg,
            related_announcement=ann,
            link_url=f"/panel/twoje-ogloszenia/{ann.id}",
            type="moderation"
        )

        coords = geocode_city(ann.location)
        if coords:
            ann.lat, ann.lng = coords
            ann.save(update_fields=["lat", "lng"])

        return {
            "id": ann.id,
            "moderation_status": moderation_status,
            "moderation_reason": moderation_reason,
            "message": msg,
        }

    @route.get("/", auth=None)
    def list_announcements(
        self,
        category: Optional[str] = Query(None),
        location: Optional[str] = Query(None),
        type: Optional[str] = Query(None),
        limit: Optional[int] = Query(None),
    ) -> List[AnnouncementOutSchema]:
        user = get_user_from_request(self.context.request)

        announcements = (
            Announcement.objects
            .select_related("user")
            .prefetch_related("images")
        )

        if category:
            categories = [c.strip() for c in category.split(",")]
            announcements = announcements.filter(category__in=categories)

        if location:
            locations = [l.strip() for l in location.split(",")]
            announcements = announcements.filter(location__in=locations)

        if type:
            announcements = announcements.filter(announcement_type=type)

        if user.is_authenticated:
            announcements = announcements.annotate(
                likes_count=Count("likes", distinct=True),
                is_liked=Exists(
                    AnnouncementLike.objects.filter(
                        announcement_id=OuterRef("pk"), user=user
                    )
                ),
            )
        else:
            announcements = announcements.annotate(
                likes_count=Count("likes", distinct=True)
            )

        announcements = announcements.filter(
            status="active", moderation_status=APPROVED).order_by("-created_at")

        if limit:
            announcements = announcements[:limit]

        return [
            AnnouncementOutSchema.model_validate(
                {
                    **a.__dict__,
                    "images": list(a.images.all()),
                    "user": a.user.username,
                    "user_id": a.user_id,
                    "status_display": a.get_status_display_label(),
                    "likes_count": a.likes_count,
                    "is_liked": getattr(a, "is_liked", False),
                },
                from_attributes=True,
            )
            for a in announcements
        ]

    @route.get("/my-announcements", auth=JWTAuthWithTokenVersion())
    def my_announcements(
        self,
        status: Optional[str] = Query(None),
        type: Optional[str] = Query(None),
        moderation_status: Optional[str] = Query(None),  # ✅ dodane
    ) -> List[AnnouncementOutSchema]:
        user = self.context.request.user
        announcements = (
            Announcement.objects.filter(user=user)
            .select_related("user")
            .prefetch_related("images")
            .annotate(
                likes_count=Count("likes", distinct=True),
                is_liked=Exists(
                    AnnouncementLike.objects.filter(
                        announcement_id=OuterRef("pk"), user=user
                    )
                )
            )
            .order_by("-created_at")
        )

        if status:
            announcements = announcements.filter(status=status)

        if type:
            announcements = announcements.filter(announcement_type=type)

        if moderation_status:  # ✅ obsługa filtra moderacji
            announcements = announcements.filter(
                moderation_status=moderation_status)

        return [
            AnnouncementOutSchema.model_validate(
                {
                    **a.__dict__,
                    "images": list(a.images.all()),
                    "user": a.user.username,
                    "user_id": a.user_id,
                    "status_display": a.get_status_display_label(),
                    "likes_count": a.likes_count,
                    "is_liked": a.is_liked,
                },
                from_attributes=True
            )
            for a in announcements
        ]

    @route.get("/{announcement_id}/likes", auth=JWTAuthWithTokenVersion())
    def get_likes(self, announcement_id: int):
        ann = get_object_or_404(Announcement, id=announcement_id)
        count = ann.likes.count()
        liked = False
        user = self.context.request.user
        if user.is_authenticated:
            liked = AnnouncementLike.objects.filter(
                announcement=ann, user=user
            ).exists()
        return {"likes_count": count, "is_liked": liked}

    @route.get("/{announcement_id}/likes/users", auth=None)
    def get_likes_users(
        self,
        announcement_id: int,
        page: int = Query(1),
        limit: int = Query(12)
    ):
        ann = get_object_or_404(Announcement, id=announcement_id)
        likes = AnnouncementLike.objects.filter(
            announcement=ann).select_related("user")

        paginator = Paginator(likes, limit)
        page_obj = paginator.get_page(page)

        return {
            "results": [
                {
                    "id": like.user.id,
                    "username": like.user.username,
                    "avatar_url": getattr(like.user, "avatar_url", None),
                }
                for like in page_obj
            ],
            "count": paginator.count,
            "total_pages": paginator.num_pages,
            "current_page": page_obj.number,
        }

    @route.get("/{announcement_id}/related", auth=None)
    def related_announcements(self, announcement_id: int, limit: int = 4):
        current = get_object_or_404(Announcement, id=announcement_id)
        user = get_user_from_request(self.context.request)
        qs = (
            Announcement.objects
            .filter(status="active")
            .filter(moderation_status=APPROVED)
            .exclude(id=current.id)
            .filter(Q(category=current.category) | Q(location=current.location))
            .annotate(
                score=Case(
                    When(location=current.location, then=2),
                    default=0,
                    output_field=IntegerField(),
                ) + Case(
                    When(category=current.category, then=1),
                    default=0,
                    output_field=IntegerField(),
                ),
                likes_count=Count("likes", distinct=True),
                is_liked=Exists(
                    AnnouncementLike.objects.filter(
                        announcement_id=OuterRef("pk"),
                        user=user if user.is_authenticated else None
                    )
                )
            )
            .select_related("user")
            .prefetch_related("images")
            .order_by("-score", "-created_at")
        )

        related = qs[: max(1, min(limit, 4))]

        return [
            AnnouncementOutSchema.model_validate(
                {
                    **a.__dict__,
                    "images": list(a.images.all()),
                    "user": a.user.username,
                    "user_id": a.user_id,
                    "status_display": a.get_status_display_label(),
                    "likes_count": a.likes_count,
                    "is_liked": a.is_liked,
                },
                from_attributes=True
            )
            for a in related
        ]

    @route.get("/nearby", auth=None)
    def nearby_announcements(
        self,
        city: str,
        radius_km: float = 50.0,
        category: Optional[str] = None,
    ):
        coords = geocode_city(city)
        if coords is None:
            return {"error": "Nie znaleziono miasta", "in_city": [], "nearby": []}

        city_lat, city_lng = coords

        qs = (
            Announcement.objects
            .filter(status="active", moderation_status=APPROVED)
            .exclude(lat=None)
            .exclude(lng=None)
            .select_related("user")
            .prefetch_related("images")
        )
        if category:
            qs = qs.filter(category=category)

        in_city = []
        nearby = []

        for ann in qs:
            dist = haversine(city_lat, city_lng, ann.lat, ann.lng)
            if dist <= radius_km:
                entry = {
                    "id": ann.id,
                    "title": ann.title,
                    "category": ann.category,
                    "location": ann.location,
                    "listing_type": ann.listing_type,
                    "distance_km": round(dist, 1),
                }
                if dist <= 5.0:
                    in_city.append(entry)
                else:
                    nearby.append(entry)

        in_city.sort(key=lambda x: x["distance_km"])
        nearby.sort(key=lambda x: x["distance_km"])

        return {
            "searched_city": city,
            "radius_km": radius_km,
            "in_city": in_city,
            "nearby": nearby,
        }

    @route.get("/{announcement_id}", auth=None)
    def get_public_announcement(self, announcement_id: int = Path(...)):
        user = get_user_from_request(self.context.request)

        ann = (
            Announcement.objects
            .select_related("user")
            .prefetch_related("images")
            .annotate(
                likes_count=Count("likes", distinct=True),
                is_liked=Exists(
                    AnnouncementLike.objects.filter(
                        announcement_id=OuterRef("pk"),
                        user=user if user.is_authenticated else None
                    )
                )
            )
            .get(id=announcement_id)
        )
        print("🔎 PUBLIC ANNOUNCEMENT", ann.id, "user:", user, "auth:",
              user.is_authenticated, "is_liked:", ann.is_liked)

        if ann.moderation_status != APPROVED:
            # jeśli właściciel lub staff, allow; inaczej 404/403
            if not (user.is_authenticated and (user.id == ann.user_id or user.is_staff)):
                return Response({"detail": "Ogłoszenie niedostępne."}, status=404)

        return AnnouncementDetailSchema.model_validate(
            {
                **ann.__dict__,
                "images": list(ann.images.all()),
                "status_display": ann.get_status_display_label(),
                "user": ann.user.username,
                "user_id": ann.user_id,
                "status": ann.status,
                "is_owner": False,
                "likes_count": ann.likes_count,
                "is_liked": ann.is_liked,
            },
            from_attributes=True
        ).model_dump()

    @route.get("/my/{announcement_id}", auth=JWTAuthWithTokenVersion())
    def get_my_announcement(self, announcement_id: int = Path(...)):
        ann = get_object_or_404(
            Announcement.objects.select_related(
                "user").prefetch_related("images"),
            id=announcement_id
        )
        user = self.context.request.user

        if ann.user_id != user.id:
            return Response({"detail": "Brak dostępu."}, status=403)

        likes_count = ann.likes.count()
        is_liked = AnnouncementLike.objects.filter(
            announcement=ann, user=user).exists()

        return AnnouncementDetailSchema.model_validate(
            {
                **ann.__dict__,
                "images": list(ann.images.all()),
                "status_display": ann.get_status_display_label(),
                "user": ann.user.username,
                "user_id": ann.user_id,
                "status": ann.status,
                "is_owner": True,
                "likes_count": likes_count,
                "is_liked": is_liked,
            },
            from_attributes=True
        ).model_dump()

    @route.post("/{announcement_id}/like", auth=JWTAuthWithTokenVersion())
    def toggle_like(self, announcement_id: int):
        user = self.context.request.user
        ensure_account_not_pending_deletion(user)

        ensure_user_verified(user)
        ann = get_object_or_404(Announcement, id=announcement_id)

        like, created = AnnouncementLike.objects.get_or_create(
            announcement=ann, user=user
        )
        if created:
            liked = True
        else:
            like.delete()
            liked = False

        count = AnnouncementLike.objects.filter(announcement=ann).count()
        return {"liked": liked, "likes_count": count}

    @route.get("/my/favorites", auth=JWTAuthWithTokenVersion())
    def my_favorites(self) -> List[AnnouncementOutSchema]:
        user = self.context.request.user
        liked_announcements = (
            Announcement.objects.filter(likes__user=user)
            .select_related("user")
            .filter(status="active", moderation_status=APPROVED)
            .prefetch_related("images")
            .annotate(
                likes_count=Count("likes", distinct=True),
                is_liked=True
            )
            .order_by("-likes__created_at")
        )

        return [
            AnnouncementOutSchema.model_validate(
                {
                    **a.__dict__,
                    "images": list(a.images.all()),
                    "user": a.user.username,
                    "user_id": a.user_id,
                    "status_display": a.get_status_display_label(),
                    "likes_count": a.likes_count,
                    "is_liked": a.is_liked,
                },
                from_attributes=True
            )
            for a in liked_announcements
        ]

    @route.delete("/my/{announcement_id}", auth=JWTAuthWithTokenVersion())
    def delete_my_announcement(self, announcement_id: int):
        user = self.context.request.user
        ensure_account_not_pending_deletion(user)

        ann = get_object_or_404(Announcement, id=announcement_id)

        if ann.user_id != user.id:
            return Response({"detail": "Brak dostępu."}, status=403)

        ann.delete()
        return {"message": "Ogłoszenie zostało usunięte."}

    @route.patch("/my/{announcement_id}", auth=JWTAuthWithTokenVersion())
    def update_status(
        self,
        announcement_id: int,
        payload: StatusUpdateSchema = Body(...),
    ):
        user = self.context.request.user
        ensure_account_not_pending_deletion(user)

        status = payload.status

        ann = get_object_or_404(Announcement, id=announcement_id, user=user)

        if status not in dict(STATUS_CHOICES):
            return {"error": "Nieprawidłowy status ogłoszenia."}

        ann.status = status
        ann.save()

        return {"message": f"Status ogłoszenia zmieniony na {status}"}

    @route.patch("/my/{announcement_id}/edit", auth=JWTAuthWithTokenVersion())
    def edit_announcement(
        self,
        announcement_id: int,
        data: AnnouncementEditSchema,
    ):
        """
        ✏️ Edycja ogłoszenia zatwierdzonego — po zapisaniu wraca do moderacji.
        MilfChecker jedynie wykrywa spam, ale nie zatwierdza automatycznie.
        """
        user = self.context.request.user
        ensure_account_not_pending_deletion(user)

        ensure_user_verified(user)
        ann = get_object_or_404(Announcement, id=announcement_id, user=user)

        # 🔒 blokada edycji niezatwierdzonych
        if ann.moderation_status in ["pending", "needs_fix"]:
            raise HttpError(
                400, "To ogłoszenie jest już w moderacji lub wymaga poprawy."
            )

        # 🧠 MilfChecker przy edycji – tylko kontrola spamu
        from announcements.utils.milfchecker import milfchecker
        mchecker_status, reason = milfchecker(data.title, data.description)

        # 🧱 aktualizacja pól
        ann.title = data.title
        ann.description = data.description
        ann.category = data.category
        ann.location = data.location
        ann.postal_code = data.postal_code or ""
        ann.listing_type = data.listing_type
        ann.email = data.email or ""
        ann.phone = data.phone or ""

        if ann.announcement_type == "private":
            ann.first_name = data.first_name or ""
        else:
            ann.company_name = data.company_name or ""
            ann.address = data.address or ""
            ann.opening_hours = data.opening_hours or ""
            ann.notes = data.notes or ""

        # 🟠 logika statusów po edycji
        if mchecker_status == "script_check_rejected":
            # MilfChecker uznał spam → blokujemy
            ann.moderation_status = "rejected_spam"
            ann.moderation_reason = (
                reason or "Treść została automatycznie oznaczona jako spam."
            )
        else:
            # zwykła edycja → wraca do moderacji
            ann.moderation_status = "pending"
            ann.moderation_reason = (
                reason or "Edycja ogłoszenia – oczekuje ponownej weryfikacji."
            )

        ann.submission_source = "edited"
        ann.visible = False
        ann.editable = False
        ann.save()

        # 🔕 powiadomienie tworzy teraz signals.py automatycznie
        return {
            "message": "Zmiany zapisane. Ogłoszenie zostało ponownie wysłane do moderacji."
        }

    @route.post("/my/{announcement_id}/images", auth=JWTAuthWithTokenVersion())
    def add_image_to_announcement(
        self,
        announcement_id: int,
        file: UploadedFile = File(...),
    ):
        user = self.context.request.user
        ensure_account_not_pending_deletion(user)

        ann = get_object_or_404(Announcement, id=announcement_id, user=user)

        if ann.images.count() >= 3:
            raise HttpError(400, "Można dodać maksymalnie 3 zdjęcia.")

        try:
            img = AnnouncementImage.objects.create(
                announcement=ann, image=file)
        except ValidationError:
            raise HttpError(400, "Nieprawidłowy format pliku.")

        return {"message": "Zdjęcie dodane", "id": img.id}

    @route.delete("/images/{image_id}", auth=JWTAuthWithTokenVersion())
    def delete_announcement_image(self, image_id: int):
        user = self.context.request.user
        ensure_account_not_pending_deletion(user)

        image = get_object_or_404(
            AnnouncementImage.objects.select_related("announcement"), id=image_id
        )

        if image.announcement.user_id != user.id:
            return Response({"detail": "Brak dostępu."}, status=403)

        if image.announcement.images.count() <= 1:
            return Response(
                {"detail": "Ogłoszenie musi mieć przynajmniej jedno zdjęcie."}, status=400
            )

        image.delete()
        return {"message": "Zdjęcie usunięte."}

    # RESUBMIT

    @route.patch("/panel/{announcement_id}/resubmit", auth=JWTAuthWithTokenVersion())
    def resubmit_announcement(
        self,
        announcement_id: int,
        data: AnnouncementEditSchema,
    ):
        """
        🔁 Ponowne wysłanie ogłoszenia po poprawkach.
        MilfChecker tylko filtruje spam – nie zatwierdza automatycznie.
        """
        user = self.context.request.user
        ensure_account_not_pending_deletion(user)
        ensure_user_verified(user)

        ann = get_object_or_404(Announcement, id=announcement_id, user=user)

        # ✅ pozwól tylko na rejected / needs_fix
        if ann.moderation_status not in ["rejected", "needs_fix"]:
            return Response(
                {"detail": f"Nie można ponownie wysłać ogłoszenia w statusie '{ann.moderation_status}'."},
                status=400,
            )

        # 🧠 MilfChecker
        from announcements.utils.milfchecker import milfchecker
        mchecker_status, reason = milfchecker(data.title, data.description)

        # 🧱 aktualizacja pól
        ann.title = data.title
        ann.description = data.description
        ann.category = data.category
        ann.location = data.location
        ann.postal_code = data.postal_code or ""
        ann.listing_type = data.listing_type
        ann.email = data.email or ""
        ann.phone = data.phone or ""

        if ann.announcement_type == "private":
            ann.first_name = data.first_name or ""
        else:
            ann.company_name = data.company_name or ""
            ann.address = data.address or ""
            ann.opening_hours = data.opening_hours or ""
            ann.notes = data.notes or ""

        # 🟡 logika moderacji
        if mchecker_status == "script_check_rejected":
            ann.moderation_status = "rejected_spam"
            ann.moderation_reason = reason or "Treść została automatycznie oznaczona jako spam."
        else:
            ann.moderation_status = "pending"
            ann.moderation_reason = reason or "Przesłano ponownie do moderacji po poprawkach."

        ann.submission_source = "resubmitted"
        ann.visible = False
        ann.editable = False
        ann.save()

        # 🔕 powiadomienie tworzy teraz signals.py automatycznie
        return {"message": "Ogłoszenie zostało ponownie wysłane do moderacji."}
