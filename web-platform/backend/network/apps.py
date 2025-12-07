from django.apps import AppConfig


class NetworkConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'network'

    def ready(self):
        import network.signals


from django.apps import AppConfig
from django.db.models.signals import post_migrate

class RolesAccessTypesConfig(AppConfig):
    name = 'network'

    def ready(self):
        import network.signals