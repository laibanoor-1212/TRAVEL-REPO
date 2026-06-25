from django.urls import path
from . import views

app_name = 'bookings'
urlpatterns = [
 path('booking/package/<int:package_id>/', views.book_package, name='book_package'),
]
