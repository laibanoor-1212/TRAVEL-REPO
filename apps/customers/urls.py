from django.urls import path
from . import views

urlpatterns = [
   
    path("customer_kyc/",views.customer_kyc,name="customer_kyc"),
     path("user_dashboard/",views.user_dashboard,name="user_dashboard"),
     path("user_bookings/",views.user_bookings,name="user_bookings"),
    
]
