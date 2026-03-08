from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import Announcement
from notifications.models import Notification


# ============================================================
# 1️⃣ pre_save — zapamiętujemy stary stan (status + submission)
# ============================================================

@receiver(pre_save, sender=Announcement)
def cache_old_state(sender, instance, **kwargs):
    if not instance.pk:
        instance._old_moderation_status = None
        instance._old_submission_source = None
        return

    try:
        old = Announcement.objects.get(pk=instance.pk)
        instance._old_moderation_status = old.moderation_status
        instance._old_submission_source = old.submission_source
    except Announcement.DoesNotExist:
        instance._old_moderation_status = None
        instance._old_submission_source = None


# ============================================================
# 2️⃣ pre_save — automatyczna zmiana submission_source
# ============================================================

@receiver(pre_save, sender=Announcement)
def set_submission_source(sender, instance, **kwargs):
    if not instance.pk:
        instance.submission_source = "new"
        return

    try:
        old = Announcement.objects.get(pk=instance.pk)
    except Announcement.DoesNotExist:
        return

    if (
        old.moderation_status == "approved"
        and instance.moderation_status == "pending"
    ):
        instance.submission_source = "edited"
    elif (
        old.moderation_status in ["rejected", "needs_fix"]
        and instance.moderation_status == "pending"
    ):
        instance.submission_source = "resubmitted"
    else:
        instance.submission_source = getattr(
            old, "submission_source", instance.submission_source)


# ============================================================
# 3️⃣ post_save — powiadomienia dla użytkownika
# ============================================================

@receiver(post_save, sender=Announcement)
def create_notification_on_moderation_change(sender, instance, created, **kwargs):
    if created:
        return  # pierwsze powiadomienie tworzy endpoint create_announcement()

    old_status = getattr(instance, "_old_moderation_status", None)
    new_status = instance.moderation_status

    if old_status == new_status:
        return

    # 🧠 zapobiega duplikatom (API już tworzyło powiadomienie tylko dla resubmitted)
    if new_status == "pending" and instance.submission_source == "resubmitted":
        return

    messages = {
        "approved": (
            "Udało się! Ogłoszenie zatwierdzone.",
            f"Twoje ogłoszenie „{instance.title}” zostało zaakceptowane i jest już widoczne publicznie.",
        ),
        "rejected": (
            "Ogłoszenie odrzucone :(",
            f"Twoje ogłoszenie „{instance.title}” zostało odrzucone przez moderatora."
            + (f" Powód: {instance.moderation_reason}" if instance.moderation_reason else ""),
        ),
        "needs_fix": (
            "Ups... Ogłoszenie wymaga poprawy",
            f"Twoje ogłoszenie „{instance.title}” wymaga poprawek."
            + (f" Powód: {instance.moderation_reason}" if instance.moderation_reason else ""),
        ),
        "pending": (
            "Ogłoszenie wysłane do ponownej moderacji",
            f"Twoje ogłoszenie „{instance.title}” zostało wysłane do ponownej weryfikacji po edycji.",
        ),
        "rejected_spam": (
            "Ogłoszenie zablokowane",
            f"Twoje ogłoszenie „{instance.title}” zostało zablokowane z powodu naruszenia zasad.",
        ),
    }

    if new_status in messages:
        title, msg = messages[new_status]
        Notification.objects.create(
            user=instance.user,
            title=title,
            message=msg,
            related_announcement=instance,
            link_url=f"/panel/twoje-ogloszenia/{instance.id}",
            type="moderation",
        )
