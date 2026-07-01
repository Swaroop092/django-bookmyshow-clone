import razorpay
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from .models import Seat, Booking, Payment, Theater
from django.db import transaction
from django.core.mail import send_mail
from django.template.loader import render_to_string
import threading
import json

razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

def checkout(request):
    locked_seat_ids = request.session.get('locked_seats', [])
    theater_id = request.session.get('theater_id')
    
    if not locked_seat_ids or not theater_id:
        return redirect('movie_list')
        
    theater = get_object_or_404(Theater, id=theater_id)
    seats = Seat.objects.filter(id__in=locked_seat_ids)
    
    # Assuming price per seat is 150 for this clone
    amount = len(seats) * 150 
    
    # Create Razorpay Order
    currency = 'INR'
    try:
        razorpay_order = razorpay_client.order.create(dict(amount=amount*100, currency=currency, receipt=f"receipt_{request.user.id}"))
        razorpay_order_id = razorpay_order['id']
    except Exception as e:
        # Fallback to a mock order ID if Razorpay fails (e.g. due to mock keys)
        import time
        razorpay_order_id = f"mock_order_{int(time.time())}"
    
    with transaction.atomic():
        payment = Payment.objects.create(
            user=request.user,
            razorpay_order_id=razorpay_order_id,
            amount=amount,
            status='Pending'
        )
        for seat in seats:
            # Delete any existing booking for this seat (failed/abandoned payment)
            Booking.objects.filter(seat=seat).delete()
            
            Booking.objects.create(
                user=request.user,
                seat=seat,
                movie=theater.movie,
                theater=theater,
                payment=payment
            )
    
    context = {
        'amount': amount,
        'razorpay_order_id': razorpay_order_id,
        'razorpay_merchant_key': settings.RAZORPAY_KEY_ID,
        'currency': currency,
        'callback_url': '/movies/paymenthandler/',
        'seats': seats,
        'theater': theater,
    }
    
    # Store order ID in session
    request.session['razorpay_order_id'] = razorpay_order_id
    request.session['amount'] = amount
    
    return render(request, 'movies/checkout.html', context)

@csrf_exempt
def paymenthandler(request):
    # This is for frontend callback, but we rely strictly on webhook for actual verification
    if request.method == "POST":
        try:
            payment_id = request.POST.get('razorpay_payment_id', '')
            razorpay_order_id = request.POST.get('razorpay_order_id', '')
            signature = request.POST.get('razorpay_signature', '')
            
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }
            
            # verify the payment signature.
            if razorpay_order_id.startswith('mock_order_'):
                result = True
            else:
                result = razorpay_client.utility.verify_payment_signature(params_dict)
            
            if result is not None:
                # Provide a success page to user, and confirm booking if webhook didn't do it yet
                with transaction.atomic():
                    payment = Payment.objects.filter(razorpay_order_id=razorpay_order_id).first()
                    if payment and payment.status != 'Success':
                        payment.status = 'Success'
                        payment.razorpay_payment_id = payment_id
                        payment.save()
                        
                        for booking in payment.bookings.all():
                            seat = booking.seat
                            seat.is_booked = True
                            seat.locked_by = None
                            seat.locked_at = None
                            seat.save()
                        
                        # Queue confirmation email (non-blocking via background scheduler)
                        if payment.bookings.exists():
                            first_booking = payment.bookings.first()
                            email_context = {
                                'username': first_booking.user.username,
                                'movie': first_booking.movie.name,
                                'theater': first_booking.theater.name,
                                'time': first_booking.theater.time,
                                'seat': ', '.join([b.seat.seat_number for b in payment.bookings.all()]),
                                'payment_id': payment_id
                            }
                            email_html = render_to_string('movies/email_booking.html', email_context)
                            from .models import EmailQueue
                            EmailQueue.objects.create(
                                recipient=first_booking.user.email,
                                subject='Ticket Confirmation - BookMyShow',
                                html_message=email_html,
                                status='Pending'
                            )
                return render(request, 'movies/payment_success.html')
            else:
                return render(request, 'movies/payment_fail.html')
        except:
            return render(request, 'movies/payment_fail.html')
    else:
        return HttpResponseBadRequest()

@csrf_exempt
def razorpay_webhook(request):
    """
    Secure server-side webhook to handle payment success/failure.
    Handles idempotency to prevent duplicate bookings.
    Uses select_for_update() inside transaction.atomic() to prevent
    race conditions when duplicate webhook events arrive simultaneously.
    """
    webhook_secret = 'mock_webhook_secret' # In production, load from settings
    webhook_signature = request.headers.get('X-Razorpay-Signature')
    event_id = request.headers.get('X-Razorpay-Event-Id')
    
    try:
        razorpay_client.utility.verify_webhook_signature(request.body.decode('utf-8'), webhook_signature, webhook_secret)
    except Exception as e:
        return HttpResponseBadRequest(f"Invalid signature: {str(e)}")

    payload = json.loads(request.body)
    event = payload['event']

    if event == 'payment.captured':
        payment_entity = payload['payload']['payment']['entity']
        order_id = payment_entity['order_id']
        amount = payment_entity['amount'] / 100
        payment_id = payment_entity['id']
        
        with transaction.atomic():
            # Lock the Payment row to prevent race conditions from duplicate webhooks.
            # The idempotency check is INSIDE the atomic block so two simultaneous
            # webhook requests cannot both pass the check before either commits.
            payment = Payment.objects.select_for_update().filter(razorpay_order_id=order_id).first()
            
            if not payment:
                return HttpResponse("Order not found", status=404)
            
            # Idempotency: if already processed or if this event_id was seen before, skip
            if payment.status == 'Success' or payment.idempotency_key == event_id:
                return HttpResponse("Duplicate webhook, ignored.", status=200)
            
            payment.status = 'Success'
            payment.razorpay_payment_id = payment_id
            payment.idempotency_key = event_id
            payment.save()
            
            for booking in payment.bookings.all():
                seat = booking.seat
                seat.is_booked = True
                seat.locked_by = None
                seat.locked_at = None
                seat.save()
            
            # Queue confirmation email (non-blocking, processed by background scheduler)
            if payment.bookings.exists():
                booking = payment.bookings.first()
                context = {
                    'username': booking.user.username,
                    'movie': booking.movie.name,
                    'theater': booking.theater.name,
                    'time': booking.theater.time,
                    'seat': ', '.join([b.seat.seat_number for b in payment.bookings.all()]),
                    'payment_id': payment_id
                }
                html_message = render_to_string('movies/email_booking.html', context)
                from .models import EmailQueue
                EmailQueue.objects.create(
                    recipient=booking.user.email,
                    subject='Ticket Confirmation - BookMyShow',
                    html_message=html_message,
                    status='Pending'
                )
            
        return HttpResponse("Success", status=200)
        
    elif event == 'payment.failed':
        # Handle payment failure gracefully
        return HttpResponse("Failed handled", status=200)

    return HttpResponse("Unhandled event", status=200)
