from django.shortcuts import get_object_or_404
from ninja_extra import api_controller, ControllerBase, route
from django.contrib.auth import get_user_model
from django.db.models import Avg
from django.core.signing import BadSignature, SignatureExpired
from django.utils import timezone

from users.auth_hooks import JWTAuthWithTokenVersion
from .schemas import ChangePasswordSchema, LoginSchema


from .models import PasswordResetToken
from .utils import generate_password_reset_token, send_password_reset_email

from utils.ensure_account_not_pending_deletion import (
    ensure_account_not_pending_deletion,
)
from utils.is_user_verified import ensure_user_verified
from utils.ratelimit import ratelimit_or_429


from .utils import generate_email_token, verify_email_token, send_verification_email
from ninja.errors import HttpError
from typing import List
from datetime import timedelta
from ninja_jwt.tokens import RefreshToken
from django.contrib.auth import authenticate


from announcements.schemas import AnnouncementOutSchema
from announcements.models import Announcement
from notifications.models import Notification


from .schemas import (
    PublicResendSchema,
    ResetPasswordSchema,
    UserOutSchema,
    RegisterSchema,
    PublicUserProfileSchema,
    ReviewInSchema,
    ReviewOutSchema,
    VerifyEmailSchema,
)
from django.db.models import Avg
from .models import Review
# constants
from announcements.constants import MODERATION_STATUS_CHOICES
MOD_STATUS = {c[0]: c[1] for c in MODERATION_STATUS_CHOICES}

PENDING = "pending"
SCRIPT_APPROVED = "script_check_approved"
SCRIPT_REJECTED = "script_check_rejected"
APPROVED = "approved"
REJECTED = "rejected"
NEEDS_FIX = "needs_fix"
REJECTED_SPAM = "rejected_spam"


User = get_user_model()


@api_controller("/users")
class UserController(ControllerBase):

    @route.get("/me", response=UserOutSchema, auth=JWTAuthWithTokenVersion())
    def me(self, request):
        return UserOutSchema(
            id=request.user.id,
            username=request.user.username,
            email=request.user.email,
            is_verified=request.user.is_verified,
            is_deleted=request.user.is_deleted,
            delete_scheduled_for=request.user.delete_scheduled_for,

        )

    @route.get("/me/score", auth=JWTAuthWithTokenVersion())
    def my_score(self, request):
        user = request.user

        # średnia ocen
        average_rating = (
            Review.objects.filter(target_user=user)
            .aggregate(avg=Avg("rating"))
            .get("avg") or 0.0
        )

        # liczba wystawionych opinii
        reviews_count = Review.objects.filter(target_user=user).count()

        return {
            "average_rating": round(average_rating, 1),
            "reviews_count": reviews_count,
        }

    @route.get("/{user_id}", response=PublicUserProfileSchema, auth=None)
    def get_public_profile(self, request, user_id: int):
        user = get_object_or_404(User, id=user_id)

        # Ogłoszenia użytkownika
        # Ogłoszenia użytkownika (tylko zatwierdzone przez moderatora)
        announcements = (
            Announcement.objects.filter(
                user=user,
                status="active",
                moderation_status=APPROVED,  # 👈 ten filtr dodajemy
            )
            .prefetch_related("images")
            .order_by("-created_at")
        )

        # Średnia ocena użytkownika
        average_rating = (
            Review.objects.filter(target_user=user)
            .aggregate(avg=Avg("rating"))
            .get("avg") or 0.0
        )

        return PublicUserProfileSchema(
            id=user.id,
            username=user.username,
            is_verified=user.is_verified,
            average_rating=round(average_rating, 1),
            announcements=[
                AnnouncementOutSchema.model_validate(
                    {
                        **a.__dict__,
                        "images": list(a.images.all()),
                        "user": a.user.username,
                        "status_display": a.get_status_display_label(),
                        "likes_count": a.likes.count(),
                        "is_liked": False,
                    },
                    from_attributes=True,
                )
                for a in announcements
            ],
        )


@api_controller("/register", tags=["Rejestracja"])
class RegisterController(ControllerBase):

    @route.post("")
    @ratelimit_or_429(rate="5/m")
    def register(self, request, data: RegisterSchema):
        if User.objects.filter(username=data.username).exists():
            raise HttpError(400, "Użytkownik o tej nazwie już istnieje")
        if User.objects.filter(email=data.email).exists():
            raise HttpError(
                400, "Użytkownik z tym adresem e-mail już istnieje")

        # Tworzymy użytkownika
        user = User.objects.create_user(
            username=data.username,
            email=data.email,
            password=data.password,
        )

        # Powiadomienie powitalne (wewnętrzne)
        Notification.objects.create(
            user=user,
            title="Witamy w Plonup!",
            message=(
                "Cieszymy się, że dołączyłeś do społeczności Plonup! \n\n"
                "Tutaj możesz dodawać i odkrywać ogłoszenia rolnicze, "
                "poznawać lokalnych producentów i dzielić się swoimi plonami.\n\n"
                "Zobacz nasz krótki przewodnik: https://plonup.pl/jak-to-dziala"
            ),
            type="welcome",
        )

        now = timezone.now()

        token = generate_email_token(user.id, now)
        send_verification_email(user.email, token)

        user.email_verification_issued_at = now
        user.save(update_fields=["email_verification_issued_at"])

        return {
            "status": "created",
            "message": "Użytkownik utworzony. Sprawdź e-mail, aby potwierdzić konto.",
            "id": user.id,
            "username": user.username,
            "email": user.email,
        }


@api_controller("/reviews", tags=["Opinie"])
class ReviewController(ControllerBase):

    @route.post("", response=ReviewOutSchema, auth=JWTAuthWithTokenVersion())
    def add_review(self, request, data: ReviewInSchema):
        ensure_account_not_pending_deletion(request.user)

        ensure_user_verified(request.user)
        if data.target_user_id == request.user.id:
            raise HttpError(400, "Nie możesz ocenić samego siebie.")

        target = get_object_or_404(User, id=data.target_user_id)

        if Review.objects.filter(author=request.user, target_user=target).exists():
            raise HttpError(400, "Już wystawiłeś opinię temu użytkownikowi.")

        review = Review.objects.create(
            author=request.user,
            target_user=target,
            rating=data.rating,
            comment=data.comment,
        )
        # 🟢 POWIADOMIENIE o nowej opinii
        Notification.objects.create(
            user=target,
            title="Nowa opinia",
            message=f"Użytkownik {request.user.username} wystawił Ci ocenę {review.rating}.",
            type="review",
            link_url="/panel/twoje-opinie",
        )

        return ReviewOutSchema.model_validate(
            {
                **review.__dict__,
                "author_username": review.author.username,
            },
            from_attributes=True,
        )

    @route.get("/me", response=List[ReviewOutSchema], auth=JWTAuthWithTokenVersion())
    def get_my_reviews(self, request):
        """Zwraca wszystkie opinie wystawione zalogowanemu użytkownikowi"""
        reviews = Review.objects.filter(
            target_user=request.user
        ).order_by("-created_at")

        return [
            ReviewOutSchema.model_validate(
                {
                    **r.__dict__,
                    "author_username": r.author.username,
                },
                from_attributes=True,
            )
            for r in reviews
        ]

    @route.get("/by-user/{user_id}", response=List[ReviewOutSchema], auth=None)
    def get_reviews_for_user(self, request, user_id: int):
        user = get_object_or_404(User, id=user_id)
        reviews = Review.objects.filter(
            target_user=user).order_by("-created_at")
        return [
            ReviewOutSchema.model_validate(
                {
                    **r.__dict__,
                    "author_username": r.author.username,
                },
                from_attributes=True,
            )
            for r in reviews
        ]
# ============================================================
# 🔐 AUTH CONTROLLER – EMAIL VERIFY
# ============================================================


@api_controller("/auth", tags=["Auth"])
class AuthController(ControllerBase):
    """
    Obsługa weryfikacji e-mail:
    - /auth/verify-email
    - /auth/resend-verification
    """

    @route.post("/verify-email")
    @ratelimit_or_429(rate="10/m")
    def verify_email(self, data: VerifyEmailSchema):

        if not data.token:
            return {"status": "invalid"}

        try:
            payload = verify_email_token(data.token)
        except SignatureExpired:
            return {"status": "expired"}
        except BadSignature:
            return {"status": "invalid"}

        user = get_object_or_404(User, id=payload["user_id"])

        # 🔒 JUŻ ZWERYFIKOWANY
        if user.is_verified:
            return {"status": "already_verified"}

        # ❌ STARY LINK
        issued_at = payload.get("issued_at")
        if not issued_at or not user.email_verification_issued_at:
            return {"status": "invalid"}

        if issued_at < user.email_verification_issued_at.timestamp():
            return {"status": "expired"}

        # ✅ POPRAWNY LINK
        user.is_verified = True
        user.save(update_fields=["is_verified"])

        return {"status": "success"}

    @route.post("/resend-verification", auth=JWTAuthWithTokenVersion())
    def resend_verification(self, request):
        user = request.user
        now = timezone.now()

        if user.is_verified:
            return {"status": "already_verified"}

        # 🔁 reset licznika po 24h
        if user.last_register_resend and now - user.last_register_resend > timedelta(hours=24):
            user.resend_register_count = 0
            user.last_register_resend = None

        # 🚫 max 3 / 24h
        if user.resend_register_count >= 3:
            raise HttpError(429, "Osiągnięto dzienny limit wysyłek.")
        # ⏳ cooldown 60s
        if user.last_register_resend and now - user.last_register_resend < timedelta(seconds=60):
            raise HttpError(429, "Poczekaj chwilę przed kolejną próbą.")

        token = generate_email_token(user.id, now)
        send_verification_email(user.email, token)

        user.resend_register_count += 1
        user.last_register_resend = now
        user.email_verification_issued_at = now

        user.save(update_fields=[
            "resend_register_count",
            "last_register_resend",
            "email_verification_issued_at",
        ])

        return {"status": "sent", "message": "Nowy link weryfikacyjny został wysłany"}

    @route.post("/public-resend-verification", response=dict)
    def public_resend_verification(self, request, data: PublicResendSchema):
        email = data.email
        now = timezone.now()

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return {"status": "ok"}  # nie zdradzamy nic

        if user.is_verified:
            return {"status": "already_verified"}

        # 🔁 reset licznika po 24h
        if user.last_register_resend and now - user.last_register_resend > timedelta(hours=24):
            user.resend_register_count = 0
            user.last_register_resend = None

        # 🚫 max 3 / 24h (TU TRZYMAMY SIĘ TWOICH ZAŁOŻEŃ)
        if user.resend_register_count >= 3:
            print("Osiągniety limit wysyłek linku aktywacyjnego")
            return {"status": "limit_reached"}
        # ⏳ cooldown 60s
        if user.last_register_resend and now - user.last_register_resend < timedelta(seconds=60):
            raise HttpError(429, "Poczekaj chwilę przed kolejną próbą.")

        token = generate_email_token(user.id, now)
        send_verification_email(user.email, token)

        user.resend_register_count += 1
        user.last_register_resend = now
        user.email_verification_issued_at = now

        user.save(update_fields=[
            "resend_register_count",
            "last_register_resend",
            "email_verification_issued_at",
        ])

        return {"status": "sent"}

    # LOGIN
    @route.post("/login")
    def login(self, data: LoginSchema):
        user = authenticate(
            username=data.username,
            password=data.password,
        )

        if not user:
            raise HttpError(401, "Niepoprawny login lub hasło")

        refresh = RefreshToken.for_user(user)

        # 🔐 KLUCZ BEZPIECZEŃSTWA
        refresh["token_version"] = user.token_version
        refresh.access_token["token_version"] = user.token_version

        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }

    # LOGOUT
    @route.post("/logout", auth=JWTAuthWithTokenVersion())
    def logout(self, request):
        request.user.token_version += 1
        request.user.save(update_fields=["token_version"])
        return {"status": "logged_out"}

    # refresh

    @route.post("/refresh", auth=None)
    def refresh(self, request):
        refresh = request.cookies.get("refresh")

        if not refresh:
            raise HttpError(401, "Brak refresh tokena")

        try:
            token = RefreshToken(refresh)
        except Exception:
            raise HttpError(401, "Nieprawidłowy refresh token")

        user_id = token.get("user_id")
        token_version = token.get("token_version")

        user = User.objects.filter(id=user_id).first()
        if not user:
            raise HttpError(401, "Użytkownik nie istnieje")

        if token_version != user.token_version:
            raise HttpError(401, "Token revoked")

        access = token.access_token
        access["token_version"] = user.token_version

        return {
            "access": str(access),
        }

    # forgot password

    @route.post("/forgot-password")
    def forgot_password(self, data: PublicResendSchema):
        try:
            user = User.objects.get(email=data.email)
        except User.DoesNotExist:
            return {"status": "ok"}  # nie zdradzamy nic

        reset = generate_password_reset_token(user)
        send_password_reset_email(user.email, reset.token)

        return {"status": "ok"}
    # RESET password:

    @route.post("/reset-password")
    def reset_password(self, data: ResetPasswordSchema):
        reset = PasswordResetToken.objects.filter(token=data.token).first()

        if not reset or not reset.is_valid():
            raise HttpError(400, "Nieprawidłowy lub wygasły token")

        user = reset.user
        user.set_password(data.password)
        user.token_version += 1
        user.save(update_fields=["password", "token_version"])

        reset.used_at = timezone.now()
        reset.save(update_fields=["used_at"])

        return {"status": "password_changed"}

    # CHANGE password
    @route.post("/change-password", auth=JWTAuthWithTokenVersion())
    def change_password(self, request, data: ChangePasswordSchema):

        ensure_account_not_pending_deletion(request.user)
        user = request.user

        if not user.check_password(data.current_password):
            raise HttpError(400, "Nieprawidłowe hasło")

        user.set_password(data.new_password)
        user.token_version += 1
        user.save(update_fields=["password", "token_version"])

        return {"status": "password_changed"}
