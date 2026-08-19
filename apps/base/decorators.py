from django.shortcuts import redirect
from functools import wraps

def role_required(role_name):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            if request.user.role != role_name:
                return redirect('base:home') 
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

def kyc_approved_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # 1. User login status check
        if not request.user.is_authenticated:
            return redirect('account_login')  # ya jo aapka login URL name hai

        # 2. Check if agent_kyc record exists on user
        if hasattr(request.user, 'agent_kyc') and request.user.agent_kyc:
            # Check kyc_status field from AgentKYC model
            if request.user.agent_kyc.kyc_status == 'approved':
                return view_func(request, *args, **kwargs)

        # 3. Agar KYC missing hai ya status 'approved' nahi hai
        return redirect('stakeholder:KYC')

    return wrapper