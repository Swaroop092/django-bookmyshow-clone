from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, Count, F, FloatField, ExpressionWrapper
from django.views.decorators.cache import cache_page
from .models import Payment, Booking, Movie, Theater, Seat

@staff_member_required
@cache_page(60 * 15) # Cache for 15 minutes
def analytics_dashboard(request):
    # Total Revenue (Sum of all Successful Payments)
    total_revenue = Payment.objects.filter(status='Success').aggregate(total=Sum('amount'))['total'] or 0

    # Most Popular Movies (By Bookings)
    popular_movies = Movie.objects.annotate(
        booking_count=Count('booking')
    ).order_by('-booking_count')[:5]

    # Busiest Theaters (By Seat Occupancy Rate)
    # Occupancy Rate = (Booked Seats / Total Seats) * 100
    theaters = Theater.objects.annotate(
        total_seats=Count('seats'),
        booked_seats=Count('seats', filter=F('seats__is_booked')==True)
    ).annotate(
        occupancy_rate=ExpressionWrapper(
            (F('booked_seats') * 100.0) / F('total_seats'),
            output_field=FloatField()
        )
    ).order_by('-occupancy_rate')[:5]

    # Cancellation Rates could be modeled similarly if we had a Cancelled status on Bookings
    # Since we don't, we can pass a placeholder or calculate based on failed payments
    failed_payments = Payment.objects.filter(status='Failed').count()
    total_payments = Payment.objects.count()
    cancellation_rate = (failed_payments / total_payments * 100) if total_payments > 0 else 0

    context = {
        'total_revenue': total_revenue,
        'popular_movies': popular_movies,
        'busiest_theaters': theaters,
        'cancellation_rate': round(cancellation_rate, 2)
    }

    return render(request, 'admin/analytics_dashboard.html', context)
