from django.urls import path
from . import views

app_name = 'bookings'
urlpatterns = [
 path('booking/package/<int:package_id>/', views.book_package, name='book_package'),
 path('<int:booking_id>/choose-payment/', views.choose_payment_method, name='choose_payment_method'),
path('<int:booking_id>/stripe-checkout/', views.stripe_checkout_page, name='stripe_checkout'),
path('<int:booking_id>/confirm-stripe/', views.confirm_stripe_payment, name='confirm_stripe_payment'),
path('<int:booking_id>/raast-payment/', views.raast_payment_page, name='raast_payment'),
path('<int:booking_id>/upload-proof/', views.upload_raast_proof, name='upload_raast_proof'),
path('<int:booking_id>/payment-status/', views.payment_status_view, name='payment_status'),
]
