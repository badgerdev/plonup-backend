from django.db.models import Q, Case, When, IntegerField, Count, Exists, OuterRef
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError

from ninja_extra import api_controller, route, ControllerBase
from ninja_jwt.authentication import JWTAuth
from ninja import File, UploadedFile, Form, Query, Path, Body
from typing import List, Optional
from ninja.responses import Response
from ninja.errors import HttpError

from announcements.constants import STATUS_CHOICES, ANNOUNCEMENT_TYPE_CHOICES, LISTING_TYPE_CHOICES
from announcements.schemas import (
    AnnouncementCreateWithImagesSchema,
    AnnouncementOutSchema,
    AnnouncementDetailSchema,
    StatusUpdateSchema,
    AnnouncementEditSchema,
)
from announcements.models import Announcement, AnnouncementImage, AnnouncementLike

VALID_CATEGORIES = [
    "owoce", "warzywa", "mięso", "nabiał", "przetwory", "słoiki", "jaja",
    "miód", "zboża", "zioła", "oleje", "pieczywo", "napoje", "inne"
]


@api_controller("/announcements", tags=["announcements"], auth=JWTAuth())
class AnnouncementController(ControllerBase):

    @route.post("/", auth=JWTAuth())
    def create_announcement(
        self,
        data: AnnouncementCreateWithImagesSchema = Form(...),
        images: List[UploadedFile] = File(default=[]),
    ):
        user = self.context.request.user

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
        )

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

        for img in images[:3]:
            AnnouncementImage.objects.create(announcement=ann, image=img)

        return {"id": ann.id, "message": "Ogłoszenie utworzone z obrazkami ✅"}

    @route.get("/", auth=None)
    def list_announcements(
        self,
        category: Optional[str] = Query(None),
        location: Optional[str] = Query(None),
        type: Optional[str] = Query(None),
        limit: Optional[int] = Query(None)
    ) -> List[AnnouncementOutSchema]:
        announcements = (
            Announcement.objects
            .select_related("user")
            .prefetch_related("images")
        )

        print("🔥 PARAMS:", category, location, type)

        if category:
            categories = [c.strip() for c in category.split(",")]
            announcements = announcements.filter(category__in=categories)

        if location:
            locations = [l.strip() for l in location.split(",")]
            announcements = announcements.filter(location__in=locations)

        if type:
            announcements = announcements.filter(announcement_type=type)

        announcements = announcements.annotate(
            likes_count=Count("likes", distinct=True)
        )

        user = self.context.request.user
        if user and user.is_authenticated:
            announcements = announcements.annotate(
                is_liked=Exists(
                    AnnouncementLike.objects.filter(
                        announcement_id=OuterRef("pk"), user=user
                    )
                )
            )

        announcements = announcements.filter(
            status="active"
        ).order_by("-created_at")

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
                    "likes_count": getattr(a, "likes_count", 0),
                    "is_liked": getattr(a, "is_liked", False) if (user and user.is_authenticated) else False,
                },
                from_attributes=True
            )
            for a in announcements
        ]

    @route.get("/locations", auth=None)
    def get_locations(self):
        return list(
            Announcement.objects.values_list(
                "location", flat=True).distinct().order_by("location")
        )

    @route.get("/my-announcements", auth=JWTAuth())
    def my_announcements(
        self,
        status: Optional[str] = Query(None),
        type: Optional[str] = Query(None),
    ) -> List[AnnouncementOutSchema]:
        user = self.context.request.user
        announcements = (
            Announcement.objects.filter(user=user)
            .select_related("user")
            .prefetch_related("images")
            .order_by("-created_at")
        )

        if status:
            announcements = announcements.filter(status=status)

        if type:
            announcements = announcements.filter(announcement_type=type)

        announcements = announcements.order_by("-created_at")
        return [
            AnnouncementOutSchema.model_validate(
                {
                    **a.__dict__,
                    "images": list(a.images.all()),
                    "user": a.user.username,
                    "user_id": a.user_id,
                    "status_display": a.get_status_display_label(),
                    "likes_count": a.likes.count(),
                    "is_liked": AnnouncementLike.objects.filter(
                        announcement=a, user=user
                    ).exists(),
                },
                from_attributes=True
            )
            for a in announcements
        ]

    @route.get("/{announcement_id}/related", auth=None)
    def related_announcements(self, announcement_id: int, limit: int = 4):
        current = get_object_or_404(Announcement, id=announcement_id)

        qs = (
            Announcement.objects
            .filter(status="active")
            .exclude(id=current.id)
            .filter(Q(category=current.category) | Q(location=current.location))
            .annotate(
                score=Case(
                    # większa waga dla lokalizacji
                    When(location=current.location, then=2),
                    default=0,
                    output_field=IntegerField(),
                ) + Case(
                    When(category=current.category, then=1),
                    default=0,
                    output_field=IntegerField(),
                )
            )
            .select_related("user")
            .prefetch_related("images")
            .order_by("-score", "-created_at")
        )

        related = qs[: max(1, min(limit, 4))]
        is_auth = self.context.request.user.is_authenticated

        return [
            AnnouncementOutSchema.model_validate(
                {
                    **a.__dict__,
                    "images": list(a.images.all()),
                    "user": a.user.username,
                    "user_id": a.user_id,
                    "status_display": a.get_status_display_label(),
                    "likes_count": a.likes.count(),
                    "is_liked": AnnouncementLike.objects.filter(
                        announcement=a, user=self.context.request.user
                    ).exists() if is_auth else False,
                },
                from_attributes=True
            )
            for a in related
        ]

    @route.get("/{announcement_id}", auth=None)
    def get_public_announcement(self, announcement_id: int = Path(...)):
        ann = get_object_or_404(
            Announcement.objects.select_related(
                "user").prefetch_related("images"),
            id=announcement_id
        )

        req = self.context.request
        return AnnouncementDetailSchema.model_validate(
            {
                **ann.__dict__,
                "images": list(ann.images.all()),
                "status_display": ann.get_status_display_label(),
                "user": ann.user.username,
                "user_id": ann.user_id,
                "status": ann.status,
                "is_owner": False,
                "likes_count": ann.likes.count(),
                "is_liked": AnnouncementLike.objects.filter(announcement=ann, user=req.user).exists()
                if req.user.is_authenticated else False,
            },
            from_attributes=True
        ).model_dump()

    @route.get("/my/{announcement_id}", auth=JWTAuth())
    def get_my_announcement(self, announcement_id: int = Path(...)):
        ann = get_object_or_404(
            Announcement.objects.select_related(
                "user").prefetch_related("images"),
            id=announcement_id
        )
        user = self.context.request.user

        if ann.user_id != user.id:
            return Response({"detail": "Brak dostępu."}, status=403)

        return AnnouncementDetailSchema.model_validate(
            {
                **ann.__dict__,
                "images": list(ann.images.all()),
                "status_display": ann.get_status_display_label(),
                "user": ann.user.username,
                "user_id": ann.user_id,
                "status": ann.status,
                "is_owner": True,
                "likes_count": ann.likes.count(),
                "is_liked": AnnouncementLike.objects.filter(announcement=ann, user=user).exists(),
            },
            from_attributes=True
        ).model_dump()

    @route.post("/{announcement_id}/like", auth=JWTAuth())
    def toggle_like(self, announcement_id: int):
        user = self.context.request.user
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

    @route.delete("/my/{announcement_id}", auth=JWTAuth())
    def delete_my_announcement(self, announcement_id: int):
        user = self.context.request.user
        ann = get_object_or_404(Announcement, id=announcement_id)

        if ann.user_id != user.id:
            return Response({"detail": "Brak dostępu."}, status=403)

        ann.delete()
        return {"message": "Ogłoszenie zostało usunięte."}

    @route.patch("/my/{announcement_id}", auth=JWTAuth())
    def update_status(
        self,
        announcement_id: int,
        payload: StatusUpdateSchema = Body(...),
    ):
        user = self.context.request.user
        status = payload.status

        ann = get_object_or_404(Announcement, id=announcement_id, user=user)

        if status not in dict(STATUS_CHOICES):
            return {"error": "Nieprawidłowy status ogłoszenia."}

        ann.status = status
        ann.save()

        return {"message": f"Status ogłoszenia zmieniony na {status}"}

    @route.patch("/my/{announcement_id}/edit", auth=JWTAuth())
    def edit_announcement(
        self,
        announcement_id: int,
        data: AnnouncementEditSchema,
    ):
        user = self.context.request.user
        ann = get_object_or_404(Announcement, id=announcement_id, user=user)

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

        ann.save()

        return {"message": "Ogłoszenie zaktualizowane pomyślnie."}

    @route.post("/my/{announcement_id}/images", auth=JWTAuth())
    def add_image_to_announcement(
        self,
        announcement_id: int,
        file: UploadedFile = File(...),
    ):
        user = self.context.request.user

        ann = get_object_or_404(Announcement, id=announcement_id, user=user)

        if ann.images.count() >= 3:
            raise HttpError(400, "Można dodać maksymalnie 3 zdjęcia.")

        try:
            img = AnnouncementImage.objects.create(
                announcement=ann, image=file)
        except ValidationError:
            raise HttpError(400, "Nieprawidłowy format pliku.")

        return {"message": "Zdjęcie dodane", "id": img.id}

    @route.delete("/images/{image_id}", auth=JWTAuth())
    def delete_announcement_image(self, image_id: int):
        user = self.context.request.user
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
