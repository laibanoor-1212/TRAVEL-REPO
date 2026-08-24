from django.urls import path
from . import views
app_name='customers'
urlpatterns = [
   
    path("customer_kyc/",views.customer_kyc,name="customer_kyc"),
     path("user_dashboard/",views.user_dashboard,name="user_dashboard"),
     path("user_bookings/",views.user_bookings,name="user_bookings"),
    
    path("overview_user/",views.overview_user,name="overview_user"),
    path("user_profile_view/",views.user_profile_view,name="user_profile_view"),
     path("customer_complaints/",views.customer_complaints,name="customer_complaints"),
      path('escrow-status/', views.escrow_status_overview, name='escrow_status'),
      path('my-tickets/', views.user_ticket, name='user_ticket'),
path('booking/<int:booking_id>/approve-ticket/', views.approve_ticket, name='approve_ticket'),
path('booking/<int:booking_id>/reject-ticket/', views.reject_ticket_view, name='reject_ticket'),

    path('detail/<int:booking_id>/', views.booking_detail, name='booking_detail'),
    path('request/<int:booking_id>/', views.manage_booking_request, name='manage_booking_request'),
  path('my-booking/<int:booking_id>/update-docs/', views.update_booking_docs, name='update_booking_docs'),
    
]
