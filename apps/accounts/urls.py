from django.urls import path
from . import views

urlpatterns = [
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("forget-password/", views.forget_password, name="forget_password"),
    path("reset-confirm/<uidb64>/<token>/",views.reset_password_confirm,name="reset_confirm"),
    
]
