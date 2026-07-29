from django.urls import path
from . import views

app_name = 'base'

urlpatterns = [
    path('', views.home, name='home'),
    path('packages/', views.packages, name='packages'),
    path('hajj-packages/', views.hajjpackages, name='hajjpackages'),
    path('guide/', views.Guide, name='Guide'),
    path('hajj-guide/', views.hajj_guide, name='hajj-guide'),
    path('ziyarat/', views.ziyarat, name='ziyarat'),
]
    path('hajj_packages/', views.hajj_packages, name='hajj_packages'),
]
