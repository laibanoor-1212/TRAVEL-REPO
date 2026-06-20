from django.urls import path
from . import views

app_name = 'bookings'
urlpatterns = [
  path('book/<int:package_id>/', views.booking, name='book_package'),
]
