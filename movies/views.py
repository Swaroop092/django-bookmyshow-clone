from django.shortcuts import render, redirect ,get_object_or_404
from .models import Movie,Theater,Seat,Booking
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction, DatabaseError
from urllib.parse import urlparse, parse_qs
from django.utils import timezone
import re

def get_youtube_embed_url(url):
    """Safely extracts a YouTube video ID and returns an embed URL.
    Uses regex to validate the video ID contains only safe characters
    (alphanumeric, hyphens, underscores) to prevent XSS injection."""
    if not url:
        return None

    try:
        parsed = urlparse(url)

        if "youtu.be" in parsed.netloc:
            video_id = parsed.path.strip("/")

        elif "youtube.com" in parsed.netloc:
            query = parse_qs(parsed.query)
            video_id = query.get("v", [None])[0]

        else:
            return None

        if not video_id:
            return None

        # Sanitize: only allow alphanumeric, hyphens, underscores (valid YouTube IDs)
        if not re.match(r'^[a-zA-Z0-9_-]+$', video_id):
            return None

        return f"https://www.youtube.com/embed/{video_id}"

    except Exception:
        return None

from .filters import MovieFilter

from django.core.paginator import Paginator
from django.db.models import Count, Q

def movie_list(request):
    queryset = Movie.objects.prefetch_related('genres', 'languages').all()
    
    sort_by = request.GET.get('sort', '')
    if sort_by == 'rating':
        queryset = queryset.order_by('-rating')
    elif sort_by == 'name':
        queryset = queryset.order_by('name')
    else:
        queryset = queryset.order_by('-id')

    movie_filter = MovieFilter(request.GET, queryset=queryset)
    filtered_qs = movie_filter.qs

    paginator = Paginator(filtered_qs, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    from .models import Genre, Language
    genres_with_counts = Genre.objects.annotate(
        movie_count=Count('movie', filter=Q(movie__in=filtered_qs))
    ).filter(movie_count__gt=0)
    
    languages_with_counts = Language.objects.annotate(
        movie_count=Count('movie', filter=Q(movie__in=filtered_qs))
    ).filter(movie_count__gt=0)

    context = {
        'filter': movie_filter, 
        'page_obj': page_obj,
        'genres_with_counts': genres_with_counts,
        'languages_with_counts': languages_with_counts,
        'sort_by': sort_by,
        'request': request
    }
    return render(request,'movies/movie_list.html', context)

def theater_list(request,movie_id):
    movie = get_object_or_404(Movie,id=movie_id)
    theater=Theater.objects.filter(movie=movie)
    embed_url = get_youtube_embed_url(movie.trailer_url)
    return render(request,'movies/theater_list.html',{'movie':movie,'theaters':theater,'embed_url':embed_url})



@login_required(login_url='/login/')
def book_seats(request,theater_id):
    theaters=get_object_or_404(Theater,id=theater_id)
    seats=Seat.objects.filter(theater=theaters)
    now = timezone.now()
    
    if request.method=='POST':
        selected_Seats = request.POST.getlist('seats')
        error_seats = []
        if not selected_Seats:
            return render(request,"movies/seat_selection.html",{'theaters':theaters,"seats":seats,'error':"No seat selected"})
        
        locked_seats = []
        try:
            with transaction.atomic():
                # select_for_update(nowait=True) acquires row-level locks immediately.
                # If another transaction holds the lock, a DatabaseError is raised
                # instead of waiting — this prevents race conditions under
                # simultaneous requests from multiple users.
                db_seats = Seat.objects.select_for_update(nowait=True).filter(id__in=selected_Seats, theater=theaters)
                
                if len(db_seats) != len(selected_Seats):
                    return render(request, "movies/seat_selection.html", {'theaters': theaters, "seats": seats, 'error': "Invalid seats selected"})
                
                for seat in db_seats:
                    if seat.is_booked:
                        error_seats.append(seat.seat_number)
                    elif seat.locked_by and seat.locked_by != request.user and seat.locked_at and (now - seat.locked_at).total_seconds() < 120:
                        error_seats.append(seat.seat_number)
                    else:
                        seat.locked_by = request.user
                        seat.locked_at = now
                        seat.save()
                        locked_seats.append(seat)
        except DatabaseError:
            # Another user is simultaneously booking these seats — row lock conflict
            return render(request, "movies/seat_selection.html", {
                'theaters': theaters,
                'seats': Seat.objects.filter(theater=theaters),
                'error': "These seats are being booked by another user. Please try again."
            })
                    
        if error_seats:
            error_message = f"The following seats are already booked or temporarily locked: {', '.join(error_seats)}"
            return render(request,'movies/seat_selection.html',{'theaters':theaters,"seats":seats,'error':error_message})
            
        # Store locked seats in session to retrieve during checkout
        request.session['locked_seats'] = [seat.id for seat in locked_seats]
        request.session['theater_id'] = theater_id
        return redirect('checkout')
        
    return render(request,'movies/seat_selection.html',{'theaters':theaters,"seats":seats})




