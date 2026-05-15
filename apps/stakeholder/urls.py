from django.urls import path
from . import views
app_name='stakeholder'

urlpatterns = [
   path("create_profile/", views.create_profile, name="create_profile"),
   
]
