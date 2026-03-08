from functools import wraps
from django_ratelimit.core import is_ratelimited
from ninja.errors import HttpError


def ratelimit_or_429(key="ip", rate="5/m"):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Ninja Extra: request zawsze w kwargs
            request = kwargs.get("request")

            if request is None:
                return func(*args, **kwargs)

            limited = is_ratelimited(
                request=request,
                key=key,
                rate=rate,
                fn=func,
                increment=True,
            )

            if limited:
                raise HttpError(
                    429,
                    "Zbyt wiele prób. Spróbuj ponownie za chwilę."
                )

            return func(*args, **kwargs)

        return wrapper
    return decorator
