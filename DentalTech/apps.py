from django.apps import AppConfig


class DentaltechConfig(AppConfig):
    name = 'DentalTech'

    def ready(self):
        from . import signals  # noqa: F401  (registra os receivers)
