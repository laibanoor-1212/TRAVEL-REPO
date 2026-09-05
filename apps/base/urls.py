from django.urls import path
from . import views

app_name = 'base'

urlpatterns = [
    path('', views.home, name='home'),
     path('contactus/', views.contactus, name='contactus'),
   
   
    path('guide/', views.Guide, name='Guide'),
    path('miqat/', views.miqat, name='miqat'),
   
    path('tawaf/', views.tawaf, name='tawaf'),
    path('Sai/', views.Sai, name='Sai'),
    path('halaq/', views.halaq, name='halaq'),
     path('mina/', views.mina, name='mina'),
      path('arafat/', views.arafat, name='arafat'),
       path('muzdalifah/', views.muzdalifah, name='muzdalifah'),
path('hajj-guide/', views.hajj_guide, name='hajj-guide'),
path("ahram/", views.ahram_guide, name="ahram"),
path("mina/", views.mina, name="mina"),
path("muzdalifah/", views.muzdalifah, name="muzdalifah"),
path("arafat/", views.arafat, name="arafat"),
path("rami/", views.rami, name="rami"),
path("qurbani/", views.qurbani, name="qurbani"),
path("tawaf-ifada/", views.tawaf_ifada, name="tawaf_ifada"),
path("tawaf-wida/", views.tawaf_wida, name="tawaf_wida"),

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
    path('search/', views.global_search, name='global_search'),
     path('travel_agent/', views.agent_list, name='agent_list'),
    path('travel_agent/<int:pk>/', views.agent_detail, name='agent_detail'),
    path('hajj_packages/', views.hajj_packages, name='hajj_packages'),
]
