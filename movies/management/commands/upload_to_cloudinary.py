from django.core.management.base import BaseCommand
from movies.models import Movie
from django.core.files import File
import os

class Command(BaseCommand):
    help = "Upload existing movie images to Cloudinary"

    def handle(self, *args, **kwargs):
        for movie in Movie.objects.all():
            if not movie.image:
                continue

            path = movie.image.path

            if os.path.exists(path):
                with open(path, "rb") as f:
                    movie.image.save(
                        os.path.basename(path),
                        File(f),
                        save=True
                    )
                self.stdout.write(self.style.SUCCESS(f"Uploaded: {movie.title}"))
            else:
                self.stdout.write(self.style.WARNING(f"Missing: {movie.title}"))