from ninja.errors import HttpError


def ensure_user_verified(user):
    """
    Globalny helper — do użycia w KAŻDYM endpointcie,
    który wymaga, aby konto było zweryfikowane.
    """
    if not user.is_verified:
        raise HttpError(
            403,
            "Wygląda na to, że nie zweryfikowałeś swojego konta. "
            "Zweryfikuj e-mail, aby uzyskać dostęp do wszystkich funkcji Plonup."
        )
