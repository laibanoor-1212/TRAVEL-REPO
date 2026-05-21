from django.urls import path
from . import views

app_name='adminpanel'

urlpatterns = [
    path('login/', views.admin_login_view, name='admin_login'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('logout/', views.admin_logout_view, name='admin_logout'),
    path('forget_password/', views.admin_forget_password, name='admin_forget_password'),
    path("reset_confirm/<uidb64>/<token>/",views.admin_reset_password_confirm, name="reset_confirm"),
    path('agent_requests',views.agent_requests,name='agent_requests'),
   path('review/<int:profile_id>/',views.review_agent, name='review_agent'), 
]