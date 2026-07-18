from django.urls import path
from . import views
app_name='customers'
urlpatterns = [
   
    path("customer_kyc/",views.customer_kyc,name="customer_kyc"),
     path("user_dashboard/",views.user_dashboard,name="user_dashboard"),
     path("user_bookings/",views.user_bookings,name="user_bookings"),
      path("user_ticket/",views.user_ticket,name="user_ticket"),
    path("overview_user/",views.overview_user,name="overview_user"),
    path("user_profile_view/",views.user_profile_view,name="user_profile_view"),
     path("customer_complaints/",views.customer_complaints,name="customer_complaints"),
      path('escrow-status/', views.escrow_status_overview, name='escrow_status'),
    
]
