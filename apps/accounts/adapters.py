from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.shortcuts import resolve_url

class CustomAccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        user = request.user
        if user.is_superuser or user.is_staff or getattr(user, 'role', '').lower() == 'admin':
            return resolve_url('adminpanel:admin_login')
        elif getattr(user, 'role', '').lower() in ['stakeholder', 'agent']:
            return resolve_url('stakeholder:KYC')
        else:
            return resolve_url('customers:user_dashboard')


# Social Account Adapter (Google Login ke liye)
class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        
        # FIX 3: Dynamic role pick up from session or URL parameters during Google Sign-up
        selected_role = request.GET.get('role') or request.POST.get('role') or request.session.get('signup_role')
        if selected_role in ['stakeholder', 'user', 'admin']:
            user.role = selected_role
            user.save()
        return user

    def get_connect_redirect_url(self, request, sociallogin):
        return self.get_login_redirect_url(request)

    def get_login_redirect_url(self, request):
        user = request.user
        if user.is_superuser or user.is_staff or getattr(user, 'role', '').lower() == 'admin':
            return resolve_url('adminpanel:admin_login')
        elif getattr(user, 'role', '').lower() in ['stakeholder', 'agent']:
            return resolve_url('stakeholder:KYC')
        else:
            return resolve_url('customers:user_dashboard')