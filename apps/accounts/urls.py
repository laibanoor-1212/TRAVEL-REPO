from django.urls import path
from . import views
app_name='accounts'
urlpatterns = [
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("forget-password/", views.forget_password, name="forget_password"),
    path("reset-confirm/<uidb64>/<token>/",views.reset_password_confirm,name="reset_confirm"),
    path('adminpanel/users/', views.admin_manage_users, name='admin_manage_users'),
    path('adminpanel/users/<int:user_id>/action/<str:status_action>/', views.change_user_status, name='change_user_status'),
    
]
