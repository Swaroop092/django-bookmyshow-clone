import json
import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.conf import settings
from movies.models import Genre, Language, Movie, Theater, Seat, Booking, Payment, EmailQueue
from django.utils.dateparse import parse_datetime


class Command(BaseCommand):
    help = 'Idempotently seed application data from data.json'

    def handle(self, *args, **options):
        # CHANGED: data_clean.json -> data.json
        fixture_path = os.path.join(settings.BASE_DIR, 'data.json')

        if not os.path.exists(fixture_path):
            self.stdout.write(
                self.style.ERROR(f"Fixture file not found at {fixture_path}")
            )
            return

        self.stdout.write("Loading fixture data from data.json...")

        with open(fixture_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Separate items by model
        by_model = {}
        for item in data:
            by_model.setdefault(item["model"], []).append(item)

        # 1. Users
        users = by_model.get("auth.user", [])
        self.stdout.write(f"Seeding {len(users)} Users...")
        for item in users:
            fields = item["fields"]

            User.objects.update_or_create(
                id=item["pk"],
                defaults={
                    "username": fields["username"],
                    "password": fields["password"],
                    "email": fields["email"],
                    "is_superuser": fields["is_superuser"],
                    "is_staff": fields["is_staff"],
                    "is_active": fields["is_active"],
                    "first_name": fields["first_name"],
                    "last_name": fields["last_name"],
                    "last_login": parse_datetime(fields["last_login"]) if fields.get("last_login") else None,
                    "date_joined": parse_datetime(fields["date_joined"]) if fields.get("date_joined") else None,
                },
            )

        # 2. Genres
        genres = by_model.get("movies.genre", [])
        self.stdout.write(f"Seeding {len(genres)} Genres...")
        for item in genres:
            Genre.objects.update_or_create(
                id=item["pk"],
                defaults={
                    "name": item["fields"]["name"],
                },
            )

        # 3. Languages
        languages = by_model.get("movies.language", [])
        self.stdout.write(f"Seeding {len(languages)} Languages...")
        for item in languages:
            Language.objects.update_or_create(
                id=item["pk"],
                defaults={
                    "name": item["fields"]["name"],
                },
            )

        # 4. Movies
        movies = by_model.get("movies.movie", [])
        self.stdout.write(f"Seeding {len(movies)} Movies...")
        for item in movies:
            fields = item["fields"]

            movie, _ = Movie.objects.update_or_create(
                id=item["pk"],
                defaults={
                    "name": fields["name"],
                    "image": fields["image"],
                    "rating": fields["rating"],
                    "cast": fields["cast"],
                    "description": fields["description"],
                    "trailer_url": fields["trailer_url"],
                },
            )

            movie.genres.set(fields.get("genres", []))
            movie.languages.set(fields.get("languages", []))

        # 5. Theaters
        theaters = by_model.get("movies.theater", [])
        self.stdout.write(f"Seeding {len(theaters)} Theaters...")
        for item in theaters:
            fields = item["fields"]

            Theater.objects.update_or_create(
                id=item["pk"],
                defaults={
                    "name": fields["name"],
                    "movie_id": fields["movie"],
                    "time": parse_datetime(fields["time"]) if fields.get("time") else None,
                },
            )

        # 6. Seats
        seats = by_model.get("movies.seat", [])
        self.stdout.write(f"Seeding {len(seats)} Seats...")
        for item in seats:
            fields = item["fields"]

            Seat.objects.update_or_create(
                id=item["pk"],
                defaults={
                    "theater_id": fields["theater"],
                    "seat_number": fields["seat_number"],
                    "is_booked": fields["is_booked"],
                    "locked_by_id": fields["locked_by"],
                    "locked_at": parse_datetime(fields["locked_at"]) if fields.get("locked_at") else None,
                },
            )

        # 7. Payments
        payments = by_model.get("movies.payment", [])
        self.stdout.write(f"Seeding {len(payments)} Payments...")
        for item in payments:
            fields = item["fields"]

            Payment.objects.update_or_create(
                id=item["pk"],
                defaults={
                    "user_id": fields["user"],
                    "razorpay_order_id": fields["razorpay_order_id"],
                    "razorpay_payment_id": fields["razorpay_payment_id"],
                    "razorpay_signature": fields["razorpay_signature"],
                    "amount": fields["amount"],
                    "status": fields["status"],
                    "idempotency_key": fields["idempotency_key"],
                    "created_at": parse_datetime(fields["created_at"]) if fields.get("created_at") else None,
                },
            )

        # 8. Bookings
        bookings = by_model.get("movies.booking", [])
        self.stdout.write(f"Seeding {len(bookings)} Bookings...")
        for item in bookings:
            fields = item["fields"]

            Booking.objects.update_or_create(
                id=item["pk"],
                defaults={
                    "user_id": fields["user"],
                    "seat_id": fields["seat"],
                    "movie_id": fields["movie"],
                    "theater_id": fields["theater"],
                    "payment_id": fields["payment"],
                    "booked_at": parse_datetime(fields["booked_at"]) if fields.get("booked_at") else None,
                },
            )

        # 9. Email Queue
        emailqueues = by_model.get("movies.emailqueue", [])
        self.stdout.write(f"Seeding {len(emailqueues)} EmailQueues...")
        for item in emailqueues:
            fields = item["fields"]

            EmailQueue.objects.update_or_create(
                id=item["pk"],
                defaults={
                    "recipient": fields["recipient"],
                    "subject": fields["subject"],
                    "html_message": fields["html_message"],
                    "status": fields["status"],
                    "retries": fields["retries"],
                    "created_at": parse_datetime(fields["created_at"]) if fields.get("created_at") else None,
                    "updated_at": parse_datetime(fields["updated_at"]) if fields.get("updated_at") else None,
                },
            )

        self.stdout.write(
            self.style.SUCCESS("Database seeding completed successfully!")
        )