from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
from django.utils import timezone


def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.info(request, "Please login first to access the admin panel.")
            return redirect('adminpanel:admin_login')
            
        if not request.user.is_superuser:
            messages.error(request, "Access Denied! You do not have admin privileges.")
            return redirect('customers:user_dashboard') 
            
        return view_func(request, *args, **kwargs)
    return _wrapped_view



def user_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.info(request, "Please login first.")
            return redirect('accounts:login')
            
        # AGAR ADMIN/SUPERUSER AANE KI KOSHISH KARE TO USKO BLOCK KAREIN
        if request.user.is_superuser:
            messages.warning(request, "Admins cannot access customer dashboards.")
            return redirect('adminpanel:admin_dashboard')  # Admin ko waapas admin dashboard bhej dein
            
        return view_func(request, *args, **kwargs)
    return _wrapped_view