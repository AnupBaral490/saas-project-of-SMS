from django.apps import AppConfig


class FeesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'fees'
    verbose_name = 'Fee Management'
    
    def ready(self):
        import fees.signals  # Register signals
