from django.urls import path
from . import views

app_name = 'base'

urlpatterns = [
    path('', views.home, name='home'),
     path('contactus/', views.contactus, name='contactus'),
   
   
    path('guide/', views.Guide, name='Guide'),
    path('miqat/', views.miqat, name='miqat'),
    path('ahram/', views.ahram, name='ahram'),
    path('tawaf/', views.tawaf, name='tawaf'),
    path('Sai/', views.Sai, name='Sai'),
    path('halaq/', views.halaq, name='halaq'),
     path('mina/', views.mina, name='mina'),
      path('arafat/', views.arafat, name='arafat'),
       path('muzdalifah/', views.muzdalifah, name='muzdalifah'),
    path('hajj-guide/', views.hajj_guide, name='hajj-guide'),
     path('iran-guide/', views.iran, name='iran'),
      path('mashad/', views.mashad, name='mashad'),
       path('qom/', views.qom, name='qom'),
        path('tehran/', views.tehran, name='tehran'),
         path('karbala/', views.karbala, name='karbala'),
    path('ziyarat/', views.ziyarat, name='ziyarat'),
    path('nabvi/', views.nabvi, name='nabvi'),
     path('riaz/', views.riaz, name='riaz'),
      path('albaqi/', views.albaqi, name='albaqi'),
       path('almustarah/', views.almustarah, name='almustarah'),
        path('algammamah/', views.algammamah, name='algammamah'),
         path('abubakar/', views.abubakar, name='abubakar'),
           path('masjidali/', views.masjidali, name='masjidali'),
            path('masjidumer/', views.masjidumer, name='masjidumer'),
             path('uhad/', views.uhad, name='uhad'),
    path('about/', views.about, name='about'),


    path('hajj_packages/', views.hajj_packages, name='hajj_packages'),
]
