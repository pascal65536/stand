from django.apps import AppConfig


class InsecureAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "insecure_app"
