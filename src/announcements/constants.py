# announcements/constants.py
from typing import Literal

# --------------------------------------
# 🔹 Typy ogłoszeń i listingu
# --------------------------------------

LISTING_TYPE_CHOICES = [
    ("sale_or_exchange", "Sprzedaż / Wymiana"),
    ("free", "Oddam za darmo"),
]

ANNOUNCEMENT_TYPE_CHOICES = [
    ("private", "Prywatne"),
    ("business", "Firmowe"),
]

STATUS_CHOICES = [
    ("active", "Aktywne"),
    ("paused", "Zawieszone"),
    ("archived", "Zarchiwizowane"),
]

# --------------------------------------
# 🔹 Statusy moderacji
# --------------------------------------

MODERATION_STATUS_CHOICES = [
    ("pending", "Oczekujące"),
    ("script_check_approved", "Automatycznie zatwierdzone przez MilfCheckera"),
    ("script_check_rejected", "Odrzucone przez skrypt"),
    ("approved", "Zatwierdzone przez moderatora"),
    ("rejected", "Odrzucone przez moderatora"),
    ("needs_fix", "Do poprawy przez użytkownika"),
    ("rejected_spam", "Zablokowane / Spam"),
]

# --------------------------------------
# 🔹 Źródło zgłoszenia (dla panelu i workflowu)
# --------------------------------------

SUBMISSION_SOURCE_CHOICES = [
    ("new", "Dodane"),
    ("edited", "Edytowane przez użytkownika"),
    ("resubmitted", "Poprawione po sprawdzeniu"),
]

# --------------------------------------
# 🔹 Typy Literal (Pydantic i Python)
# --------------------------------------

ListingType = Literal["sale_or_exchange", "free"]
AnnouncementType = Literal["private", "business"]
StatusType = Literal["active", "paused", "archived"]
ModerationStatusType = Literal[
    "pending",
    "script_check_approved",
    "script_check_rejected",
    "approved",
    "rejected",
    "needs_fix",
    "rejected_spam",
]
SubmissionSourceType = Literal["new", "edited", "resubmitted"]
