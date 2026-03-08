from ninja_jwt.tokens import AccessToken
from django.contrib.auth import get_user_model

User = get_user_model()


def get_user_from_request(request):
    """
    Próbuje wyciągnąć usera z JWT:
    - najpierw z ciasteczka 'access'
    - jeśli brak, to z nagłówka Authorization: Bearer ...
    """
    token = request.COOKIES.get("access")

    # 🔥 dodajemy obsługę nagłówka
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split("Bearer ")[1]

    print("🍪/🔑 token in request:", token)

    if not token:
        return request.user

    try:
        access_token = AccessToken(token)
        user_id = access_token["user_id"]
        user = User.objects.get(id=user_id)
        print("✅ JWT decoded, user:", user)
        return user
    except Exception as e:
        print("⚠️ JWT decode error in get_user_from_request:", e)
        return request.user
