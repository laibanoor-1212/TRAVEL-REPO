from django.urls import path
from . import views

app_name = 'base'
urlpatterns = [
    path('hajj_packages/', views.hajj_packages, name='hajj_packages'),
]
