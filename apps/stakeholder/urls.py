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
   
]
