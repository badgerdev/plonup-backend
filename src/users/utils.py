from datetime import timedelta
from django.utils import timezone
import secrets
from django.conf import settings
from django.core import signing
from django.core.mail import send_mail

from users.models import PasswordResetToken

# -------------------------------------------------------------
# 🔐 GENERATE TOKEN
# -------------------------------------------------------------


def generate_email_token(user_id: int, issued_at) -> str:
    return signing.dumps(
        {
            "user_id": user_id,
            "issued_at": issued_at.timestamp(),
        },
        salt="email-verification",
    )


# -------------------------------------------------------------
# 🔐 VERIFY TOKEN
# -------------------------------------------------------------
def verify_email_token(token: str, max_age_hours: int = 24):
    return signing.loads(
        token,
        salt="email-verification",
        max_age=max_age_hours * 3600,
    )
# -------------------------------------------------------------
# 📬 EMAIL (Django SMTP)
# -------------------------------------------------------------


def send_verification_email(email: str, token: str):
    verify_url = f"{settings.FRONTEND_URL}/potwierdz?token={token}"

    html = f"""
        <h2>Witaj w Plonup! 🌾</h2>
        <p>Kliknij poniższy przycisk, aby potwierdzić swój adres e-mail:</p>

        <p>
            <a
                href="{verify_url}"
                style="padding: 10px 20px; background: #ff7f00; color: white;
                       text-decoration: none; border-radius: 8px;">
                Potwierdź e-mail
            </a>
        </p>

        <p>Lub skopiuj ten link do przeglądarki:<br>{verify_url}</p>

        <p>Link jest ważny przez 24 godziny.</p>

        <p>Pozdrawiamy!<br>Zespół Plonup</p>
    """

    try:
        send_mail(
            subject="Potwierdź swój adres e-mail w Plonup",
            message=f"Potwierdź e-mail: {verify_url}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html,
            fail_silently=False,
        )
        print("📨 Mail aktywacyjny wysłany do:", email)
    except Exception as e:
        print("❌ Błąd wysyłki maila:", e)


def generate_password_reset_token(user):
    token = secrets.token_urlsafe(48)

    return PasswordResetToken.objects.create(
        user=user,
        token=token,
        expires_at=timezone.now() + timedelta(hours=1),
    )


def send_password_reset_email(email: str, token: str):
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"

    html = f"""
    <h2>Reset hasła – Plonup</h2>
    <p>Kliknij, aby ustawić nowe hasło:</p>
    <p><a href="{reset_url}">{reset_url}</a></p>
    <p>Link ważny 1 godzinę.</p>
    """

    try:
        send_mail(
            subject="Reset hasła – Plonup",
            message=f"Reset hasła: {reset_url}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html,
            fail_silently=False,
        )
        print("📨 Mail resetujący hasło wysłany do:", email)
    except Exception as e:
        print("❌ Błąd wysyłki maila:", e)
