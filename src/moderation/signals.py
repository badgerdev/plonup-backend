from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Report
from notifications.models import Notification
from django.contrib.auth import get_user_model

User = get_user_model()


@receiver(post_save, sender=Report)
def notify_moderators_on_new_report(sender, instance, created, **kwargs):
    """Automatyczne powiadomienie dla moderatorów o nowym zgłoszeniu."""
    if not created:
        return

    # wysyłamy do wszystkich moderatorów (is_staff=True)
    moderators = User.objects.filter(is_staff=True)

    for mod in moderators:
        Notification.objects.create(
            user=mod,
            title="Nowe zgłoszenie użytkownika",
            message=(
                f"Użytkownik {instance.reported_by.username} zgłosił "
                f"{instance.get_target_type_display().lower()} #{instance.target_id}.\n"
                f"Powód: {instance.reason[:150]}..."
            ),
            type="system",
            link_url="/admin/moderation/report/",
        )
