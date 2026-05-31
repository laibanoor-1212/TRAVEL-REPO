from django.urls import path
from . import views

urlpatterns = [
   
    path("customer_kyc/",views.customer_kyc,name="customer_kyc"),
    
]
