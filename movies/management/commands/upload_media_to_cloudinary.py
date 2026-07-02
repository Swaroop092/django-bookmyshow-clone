import os
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files.storage import default_storage
from movies.models import Movie

class Command(BaseCommand):
    help = 'Upload local media files to Cloudinary (or current default storage)'

    def handle(self, *args, **options):
        storage_class_name = default_storage.__class__.__name__
        self.stdout.write(f"Current default storage class: {storage_class_name}")

        is_cloudinary = 'Cloudinary' in storage_class_name
        if not is_cloudinary:
            self.stdout.write(self.style.WARNING(
                "WARNING: Cloudinary is not configured as default storage. "
                "This command will upload files to whatever storage is active."
            ))

        movies = Movie.objects.all()
        self.stdout.write(f"Found {movies.count()} movies to process.")

        for movie in movies:
            if not movie.image:
                self.stdout.write(f"Movie '{movie.name}' (ID: {movie.id}) has no image associated.")
                continue

            image_name = movie.image.name
            self.stdout.write(f"Processing '{movie.name}': file '{image_name}'...")

            # Local path where git-committed media should exist
            local_path = os.path.join(settings.MEDIA_ROOT, image_name)

            if not os.path.exists(local_path):
                self.stdout.write(self.style.ERROR(
                    f"Local file not found at: {local_path}"
                ))
                continue

            # Check if file already exists in remote storage to prevent redundant uploads
            if default_storage.exists(image_name):
                self.stdout.write(self.style.SUCCESS(
                    f"File '{image_name}' already exists in target storage. Skipping upload."
                ))
            else:
                self.stdout.write(f"Uploading '{image_name}' ({os.path.getsize(local_path)} bytes)...")
                try:
                    with open(local_path, 'rb') as f:
                        saved_name = default_storage.save(image_name, f)
                    self.stdout.write(self.style.SUCCESS(
                        f"Successfully uploaded '{image_name}' as '{saved_name}'."
                    ))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f"Failed to upload '{image_name}': {str(e)}"
                    ))

        self.stdout.write(self.style.SUCCESS("Media sync process finished!"))
