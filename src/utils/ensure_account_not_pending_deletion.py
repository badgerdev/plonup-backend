# utils/ensure_account_not_pending_deletion.py
from ninja.errors import HttpError


def ensure_account_not_pending_deletion(user):
    if user.is_deleted:
        raise HttpError(
            403,
            "ACCOUNT_DELETION_PENDING"
        )
