import re
import unicodedata
from announcements.constants import MODERATION_STATUS_CHOICES

MOD_STATUS = {c[0]: c[1] for c in MODERATION_STATUS_CHOICES}

PENDING = "pending"
SCRIPT_APPROVED = "script_check_approved"
SCRIPT_REJECTED = "script_check_rejected"
APPROVED = "approved"
REJECTED = "rejected"
NEEDS_FIX = "needs_fix"
REJECTED_SPAM = "rejected_spam"


# 💣 Baza brzydkich słów (rozszerzymy ją niżej)
BANNED_WORDS = [
    "sex", "seks", "secks", "s€x", "s3x", "porno", "p0rno", "anal", "analny", "analna",
    "analne", "cipka", "cipki", "cipa", "pipa", "pizda", "pizdy", "kutas", "kutasy",
    "kutaska", "chuj", "chuje", "chujem", "chujek", "chujowy", "huj", "huje", "kurwa",
    "kurwy", "kurewka", "kurewska", "dziwka", "dziwki", "jebanie", "jebac", "jebie",
    "jebany", "pierdolic", "pierdol", "orgazm", "orgazmy", "burdel", "burdele",
    "mamuśki", "mamuski", "nastolatki", "nastolatka", "rozbierane", "rozbierana",
    "escort", "eskorta", "prostytutka", "prostytucja", "seksowny", "seksowna", "nago",
    "nagość", "naga", "nagi", "nagie", "nagranie", "nagrania", "cycki", "biust",
    "biusty", "dupeczka", "dupeczki", "dupa", "dupy", "dupcia", "dupciunia", "ruchanie",
    "ruchac", "ruchaj", "twardy", "mokro", "mokra", "mokre", "sperma", "spermik",
    "penis", "penisy", "kutasek", "cipunie", "cipunia", "cipuniaa", "cipciak",
    "cipciunia", "lizanie", "lizac", "blowjob", "handjob", "deepthroat", "fisting",
    "gangbang", "hardcore", "softcore", "erotyka", "erotyczny", "erotyczna", "randka",
    "randki", "randkowac", "sponsoring", "sponsor", "sponsorka", "sponsorowany",
    "fetysz", "fetysze", "bdsm", "gej", "lesbijka", "trojkat", "trójkąt", "masturbacja",
    "masturbowac", "dildo", "wibrator", "seksik", "sexik"
]


def normalize_text(text: str) -> str:
    """Usuwa polskie znaki, znaki specjalne i spacje."""
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    text = text.encode("ascii", "ignore").decode("utf-8")
    text = re.sub(r"[^a-z0-9\s]", "", text)  # usuń znaki specjalne
    text = re.sub(r"\s+", "", text)  # usuń spacje całkowicie
    return text


def milfchecker(title: str, description: str):
    """Automatyczna weryfikacja treści ogłoszenia."""
    combined = normalize_text(f"{title} {description}")

    for banned in BANNED_WORDS:
        if banned in combined:
            return SCRIPT_REJECTED, f"Wykryto niedozwolone słowo: {banned}"

    return SCRIPT_APPROVED, "Automatyczna weryfikacja przeszła pomyślnie."
