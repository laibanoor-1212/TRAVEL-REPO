from django.urls import path
from . import views

# Agar aapne app_name set kiya hua hai (e.g., app_name = 'notifications')
app_name = 'notifications' 

urlpatterns = [
    # Baqi ke URL paths...
    
    # Yeh path add karein mark_as_read ke liye
    path('notification/read/<slug:slug>/', views.mark_as_read, name='mark_as_read'),
]