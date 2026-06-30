from django.apps import AppConfig


class MoviesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'movies'

    def ready(self):
        import os
        # Only start the scheduler in the main process
        if os.environ.get('RUN_MAIN', None) == 'true':
            from . import scheduler
            scheduler.start()
