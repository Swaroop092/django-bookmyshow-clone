from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, Count, F, FloatField, ExpressionWrapper, Q
from django.views.decorators.cache import cache_page
from django.utils import timezone
from datetime import timedelta
from .models import Payment, Booking, Movie, Theater, Seat

@staff_member_required
@cache_page(60 * 15) # Cache for 15 minutes
def analytics_dashboard(request):
    now = timezone.now()
    
    # Total Revenue (Sum of all Successful Payments)
    total_revenue = Payment.objects.filter(status='Success').aggregate(total=Sum('amount'))['total'] or 0

    # Daily Revenue (today)
    daily_revenue = Payment.objects.filter(
        status='Success',
        created_at__date=now.date()
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Weekly Revenue (last 7 days)
    week_ago = now - timedelta(days=7)
    weekly_revenue = Payment.objects.filter(
        status='Success',
        created_at__gte=week_ago
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Monthly Revenue (last 30 days)
    month_ago = now - timedelta(days=30)
    monthly_revenue = Payment.objects.filter(
        status='Success',
        created_at__gte=month_ago
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Most Popular Movies (By Bookings)
    popular_movies = Movie.objects.annotate(
        booking_count=Count('booking')
    ).order_by('-booking_count')[:5]

    # Busiest Theaters (By Seat Occupancy Rate)
    # Occupancy Rate = (Booked Seats / Total Seats) * 100
    theaters = Theater.objects.annotate(
        total_seats=Count('seats'),
        booked_seats=Count('seats', filter=Q(seats__is_booked=True))
    ).annotate(
        occupancy_rate=ExpressionWrapper(
            (F('booked_seats') * 100.0) / F('total_seats'),
            output_field=FloatField()
        )
    ).order_by('-occupancy_rate')[:5]

    # Peak Booking Hours (group bookings by hour of day)
    peak_hours = Booking.objects.extra(
        select={'hour': 'strftime("%%H", booked_at)'}
    ).values('hour').annotate(
        booking_count=Count('id')
    ).order_by('-booking_count')[:5]

    # Cancellation Rates
    failed_payments = Payment.objects.filter(status='Failed').count()
    total_payments = Payment.objects.count()
    cancellation_rate = (failed_payments / total_payments * 100) if total_payments > 0 else 0

    context = {
        'total_revenue': total_revenue,
        'daily_revenue': daily_revenue,
        'weekly_revenue': weekly_revenue,
        'monthly_revenue': monthly_revenue,
        'popular_movies': popular_movies,
        'busiest_theaters': theaters,
        'peak_hours': peak_hours,
        'cancellation_rate': round(cancellation_rate, 2)
    }

    return render(request, 'admin/analytics_dashboard.html', context)
