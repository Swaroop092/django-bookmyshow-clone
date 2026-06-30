import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookmyseat.settings')
django.setup()

from movies.models import Movie, Genre, Language, Theater, Seat
from django.core.files.base import ContentFile
import random
from datetime import datetime, timedelta
from django.utils import timezone

# Add Genres
genres = ['Action', 'Comedy', 'Drama', 'Sci-Fi', 'Thriller']
genre_objs = []
for g in genres:
    obj, created = Genre.objects.get_or_create(name=g)
    genre_objs.append(obj)

# Add Languages
languages = ['English', 'Hindi', 'Telugu', 'Tamil']
lang_objs = []
for l in languages:
    obj, created = Language.objects.get_or_create(name=l)
    lang_objs.append(obj)

movies_data = [
    {
        'name': 'Inception 2',
        'rating': 9.2,
        'cast': 'Leonardo DiCaprio, Tom Hardy',
        'description': 'A mind-bending sci-fi thriller about dream sharing.',
        'trailer_url': 'https://www.youtube.com/watch?v=YoHD9XEInc0'
    },
    {
        'name': 'The Avengers: Return',
        'rating': 8.8,
        'cast': 'Robert Downey Jr., Chris Evans',
        'description': 'Earth\'s mightiest heroes reunite to save the world again.',
        'trailer_url': 'https://www.youtube.com/watch?v=eOrNdBpGMv8'
    },
    {
        'name': 'Comedy Nights: The Movie',
        'rating': 7.5,
        'cast': 'Kevin Hart, Dwayne Johnson',
        'description': 'A hilarious adventure across the globe.',
        'trailer_url': 'https://www.youtube.com/watch?v=1rPxiXXxvkE'
    },
    {
        'name': 'Baahubali 3: The Legacy',
        'rating': 9.5,
        'cast': 'Prabhas, Rana Daggubati',
        'description': 'The epic saga continues in the kingdom of Mahishmati.',
        'trailer_url': 'https://www.youtube.com/watch?v=qD-6d8Wo3do'
    },
    {
        'name': 'Mission Impossible: Final',
        'rating': 8.9,
        'cast': 'Tom Cruise, Rebecca Ferguson',
        'description': 'Ethan Hunt faces his most dangerous mission yet.',
        'trailer_url': 'https://www.youtube.com/watch?v=2m1drlOZSDw'
    }
]

# Create a simple dummy image
dummy_image_content = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'

for data in movies_data:
    movie, created = Movie.objects.get_or_create(name=data['name'], defaults={
        'rating': data['rating'],
        'cast': data['cast'],
        'description': data['description'],
        'trailer_url': data['trailer_url']
    })
    
    if created:
        movie.image.save('dummy.gif', ContentFile(dummy_image_content), save=True)
        movie.genres.add(random.choice(genre_objs))
        movie.languages.add(random.choice(lang_objs))
        movie.save()
        
        # Add theaters for the movie
        theater_names = ['PVR Cinemas', 'INOX', 'Cinepolis', 'Carnival Cinemas']
        for i in range(random.randint(1, 3)):
            t_name = random.choice(theater_names)
            t_time = timezone.now() + timedelta(days=random.randint(1, 7), hours=random.randint(10, 22))
            theater = Theater.objects.create(name=t_name, movie=movie, time=t_time)
            
            # Generate seats for the theater
            seats_to_create = []
            for row in ['A', 'B', 'C', 'D', 'E']:
                for num in range(1, 11):
                    seat_number = f"{row}{num}"
                    seats_to_create.append(Seat(theater=theater, seat_number=seat_number))
            Seat.objects.bulk_create(seats_to_create)

print("Movies, theaters, and seats successfully added!")
