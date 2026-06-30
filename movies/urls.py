from django.urls import path
from . import views
from . import payments

urlpatterns=[
    path('',views.movie_list,name='movie_list'),
    path('<int:movie_id>/theaters',views.theater_list,name='theater_list'),
    path('theater/<int:theater_id>/seats/book/',views.book_seats,name='book_seats'),
    path('checkout/', payments.checkout, name='checkout'),
    path('paymenthandler/', payments.paymenthandler, name='paymenthandler'),
    path('webhook/razorpay/', payments.razorpay_webhook, name='razorpay_webhook'),
]