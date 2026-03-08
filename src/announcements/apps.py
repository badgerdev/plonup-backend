from django.apps import AppConfig


class AnnouncementsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'announcements'

    # wczytanie sygnałów przy starcie
    def ready(self):
        import announcements.signals
