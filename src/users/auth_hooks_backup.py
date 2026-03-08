from ninja_jwt.authentication import JWTAuth
from ninja_jwt.exceptions import InvalidToken
from ninja_jwt.tokens import AccessToken


class JWTAuthWithTokenVersion(JWTAuth):
    def authenticate(self, request, token):
        # 1️⃣ standardowa walidacja JWT (exp, signature)
        user = super().authenticate(request, token)

        # 2️⃣ dekodujemy payload SAMI
        try:
            decoded = AccessToken(token)
        except Exception:
            raise InvalidToken("Invalid token")

        token_version = decoded.get("token_version")
        if token_version != user.token_version:
            raise InvalidToken("Token revoked")

        return user
