from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from urllib.parse import urlparse


def validate_youtube_url(value):
    allowed_domains = [
        "www.youtube.com",
        "youtube.com",
        "youtu.be"
    ]

    parsed = urlparse(value)

    if parsed.netloc not in allowed_domains:
        raise ValidationError(
            "Only YouTube URLs are allowed."
        )

class Genre(models.Model):
    name = models.CharField(max_length=50, unique=True)
    def __str__(self):
        return self.name

class Language(models.Model):
    name = models.CharField(max_length=50, unique=True)
    def __str__(self):
        return self.name

class Movie(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    image = models.ImageField(upload_to="movies/")
    rating = models.DecimalField(max_digits=3, decimal_places=1, db_index=True)
    cast = models.TextField()
    description = models.TextField(blank=True, null=True)

    # NEW FIELD
    trailer_url = models.URLField(
        blank=True,
        null=True,
        validators=[validate_youtube_url]
    )
    genres = models.ManyToManyField(Genre, blank=True)
    languages = models.ManyToManyField(Language, blank=True)

    def __str__(self):
        return self.name


class Theater(models.Model):
    name = models.CharField(max_length=255)
    movie = models.ForeignKey(
        Movie,
        on_delete=models.CASCADE,
        related_name='theaters'
    )
    time = models.DateTimeField()

    def __str__(self):
        return f'{self.name} - {self.movie.name} at {self.time}'


class Seat(models.Model):
    theater = models.ForeignKey(
        Theater,
        on_delete=models.CASCADE,
        related_name='seats'
    )
    seat_number = models.CharField(max_length=10)
    is_booked = models.BooleanField(default=False)
    locked_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='locked_seats')
    locked_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.seat_number} in {self.theater.name}'


class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    seat = models.OneToOneField(Seat, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    theater = models.ForeignKey(Theater, on_delete=models.CASCADE)
    payment = models.ForeignKey('Payment', on_delete=models.CASCADE, null=True, blank=True, related_name='bookings')
    booked_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Booking by {self.user.username} for {self.seat.seat_number} at {self.theater.name}'

class Payment(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Success', 'Success'),
        ('Failed', 'Failed'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    razorpay_order_id = models.CharField(max_length=100, unique=True)
    razorpay_payment_id = models.CharField(max_length=100, null=True, blank=True)
    razorpay_signature = models.CharField(max_length=200, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    idempotency_key = models.CharField(max_length=255, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.booking.user.username} - {self.razorpay_order_id} - {self.status}'

class EmailQueue(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Sent', 'Sent'),
        ('Failed', 'Failed'),
    )
    recipient = models.EmailField()
    subject = models.CharField(max_length=255)
    html_message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    retries = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.recipient} - {self.subject} - {self.status}"