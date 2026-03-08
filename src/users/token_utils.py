from datetime import datetime, timedelta
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from .models import BlacklistedRefreshToken


def blacklist_refresh_token(refresh_token: str):
    """
    Dodaje pojedynczy refresh token do blacklisty.
    """
    token = RefreshToken(refresh_token)

    jti = token["jti"]
    exp_timestamp = token["exp"]
    expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)

    BlacklistedRefreshToken.objects.get_or_create(
        jti=jti,
        defaults={
            "user_id": token["user_id"],
            "expires_at": expires_at,
        },
    )


def blacklist_all_user_tokens(user):
    """
    Logicznie unieważnia WSZYSTKIE refresh tokeny użytkownika.
    Robimy to przez znacznik czasu.
    """
    # W praktyce: przy refreshie sprawdzimy revoked_after
    user.last_logout_at = timezone.now()
    user.save(update_fields=["last_logout_at"])
