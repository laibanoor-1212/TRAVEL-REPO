from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = 'accounts:login'

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and (user.is_superuser or user.is_staff or user.role == 'admin')

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            messages.error(self.request, "You must be logged in to access this page.")
            return redirect('accounts:login')
        
        # Unauthorized access par 'no_access' page par bhejne ke liye
        messages.error(self.request, "You do not have permission to access the admin panel.")
        return redirect('base:no_access')  # Apne no access view ka URL name likhein


class ApprovedAgentRequiredMixin(LoginRequiredMixin):
    login_url = 'accounts:login'

    def dispatch(self, request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            messages.error(request, "You must be logged in to access this page.")
            return redirect('accounts:login')

        # 1. Agar Admin, Stakeholder route access kare -> No Access Page
        if user.is_superuser or user.is_staff or user.role == 'admin':
            messages.warning(request, "Admins are not allowed to access the Stakeholder dashboard.")
            return redirect('base:no_access')

        # 2. Agar Normal Customer, Stakeholder route access kare -> No Access Page
        if user.role != 'stakeholder':
            messages.error(request, "Only stakeholders can access this section.")
            return redirect('base:no_access')

        # 3. Agent Profile / KYC Status validation
        agent_profile = getattr(user, 'agent_profile', None)
        if not agent_profile:
            messages.error(request, "Stakeholder profile not found.")
            return redirect('accounts:login')

        if agent_profile.kyc_status == 'rollback':
            messages.warning(request, "Your KYC has been sent back for corrections.")
            return redirect('stakeholder:missing_doc')
        elif agent_profile.kyc_status == 'pending':
            messages.info(request, "Your KYC is under review.")
            return redirect('stakeholder:request_pending')
        elif agent_profile.kyc_status == 'rejected':
            messages.error(request, "Your KYC has been rejected.")
            return redirect('stakeholder:account_locked')
        elif agent_profile.kyc_status == 'approved':
            return super().dispatch(request, *args, **kwargs)
        else:
            messages.error(request, "Invalid KYC status.")
            return redirect('accounts:login')


class CustomerRequiredMixin(LoginRequiredMixin):
    login_url = 'accounts:login'

    def dispatch(self, request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            messages.error(request, "You must be logged in to access this page.")
            return redirect('accounts:login')

        # 1. Agar Admin, Customer route access kare -> No Access Page
        if user.is_superuser or user.is_staff or user.role == 'admin':
            messages.warning(request, "Admins are not allowed to access the Customer dashboard.")
            return redirect('base:no_access')

        # 2. Agar Stakeholder, Customer route access kare -> No Access Page
        if user.role == 'stakeholder':
            messages.error(request, "Stakeholders are not allowed to access Customer pages.")
            return redirect('base:no_access')

        # 3. Regular 'user' check
        if user.role != 'user':
            messages.error(request, "You do not have customer access rights.")
            return redirect('base:no_access')

        return super().dispatch(request, *args, **kwargs)