import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookmyseat.settings')
django.setup()

from movies.models import Theater, Seat

for theater in Theater.objects.all():
    if theater.seats.count() < 10:
        seats_to_create = []
        for row in ['A', 'B', 'C', 'D', 'E']:
            for num in range(1, 11):
                seat_number = f"{row}{num}"
                if not Seat.objects.filter(theater=theater, seat_number=seat_number).exists():
                    seats_to_create.append(Seat(theater=theater, seat_number=seat_number))
        
        Seat.objects.bulk_create(seats_to_create)
        print(f"Created {len(seats_to_create)} seats for theater {theater.name}")
    else:
        print(f"Theater {theater.name} already has {theater.seats.count()} seats.")
