from django.urls import path
from . import views

app_name='stakeholder'

urlpatterns = [
   path("KYC/", views.agent_kyc_view, name="KYC"),
#  path('logout/', views.logout_view, name='logout'),
   path("agent_approved/", views.approved_agent, name="approved_agent"),
   path("request_pending/", views.request_pending, name="request_pending"),
   path("agent_details/", views.agent_details, name="create_profile"),
   path("missing_doc/", views.missing_doc, name="missing_doc"),
   path("account_locked/", views.account_locked, name="account_locked"),
    path("view_profile/", views.view_profile, name="view_profile"),
   path("dashboard/", views.stakeholder_dashboard, name="stakeholder_dashboard"),
   
   path("manage_booking/", views.manage_booking, name="manage_booking"),
   path("earning_transaction/", views.earning_transaction, name="earning_transaction"),
   path("payments/", views.payments, name="payments"),
   path('escrow-status/', views.escrow_status_overview, name='escrow_status'),
   path('booking/<int:booking_id>/upload-ticket/', views.agent_upload_ticket, name='agent_upload_ticket'),
    path("agent_complaints/", views.agent_complaints, name="agent_complaints"),
      path("cancelled_booking/", views.cancelled_booking, name="cancelled_booking"),
    path(
        'create-package/',
        views.create_packages,
        name='create_packages'
    ),
    

    path(
        'manage-packages/',
        views.manage_packages,
        name='manage_packages'
    ),

    path(
        'update-package/<int:pk>/',
        views.update_package,
        name='update_package'
    ),

    path(
        'delete-package/<int:pk>/',
        views.delete_package,
        name='delete_package'
    ),

    path('booking/<int:booking_id>/details/', views.booking_detail_view, name='booking_detail'),
     

   
]
