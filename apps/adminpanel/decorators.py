from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.info(request, "Please login first to access the admin panel.")
            return redirect('admin_login')
        if not request.user.is_superuser:
            messages.error(request, "Access Denied! You do not have admin privileges.")
            return redirect('user_dashboard')
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view
