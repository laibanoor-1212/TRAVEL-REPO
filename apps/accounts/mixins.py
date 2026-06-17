from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    UserPassesTestMixin
)
from django.core.exceptions import PermissionDenied


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):

    login_url = 'accounts:login'

    def test_func(self):
        return self.request.user.is_superuser

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:

            messages.error(self.request,"You must logged in to access this page.")
            return redirect('accounts:login')
        messages.error(self.request,"You do not have permission to access the admin panel.")
        return redirect('accounts:login')


class ApprovedAgentRequiredMixin(LoginRequiredMixin):

    login_url = 'accounts:login'

    def dispatch(self, request, *args, **kwargs):

        user = request.user
        if not user.is_authenticated:

            messages.error(request,"You must logged in to access this page.")
            return redirect('accounts:login')
        agent_profile = getattr(user, 'agent_profile', None)
        if not agent_profile:
            messages.error(request,"Agent profile not found.")
            return redirect('accounts:login')
        if agent_profile.kyc_status == 'rollback':

            messages.warning(request,"Your KYC has been sent back for corrections.")
            return redirect('stakeholder:missing_doc')
        elif agent_profile.kyc_status == 'pending':

            messages.info(request,"Your KYC is under review.")

            return redirect('stakeholder:request_pending')
        elif agent_profile.kyc_status == 'rejected':
            messages.error(request,"Your KYC has been rejected.")
            return redirect('stakeholder:account_locked')
        elif agent_profile.kyc_status == 'approved':
            return super().dispatch(request, *args, **kwargs)
        else:
            messages.error( request,"Invalid KYC status.")
            return redirect('accounts:login')
class CustomerRequiredMixin(LoginRequiredMixin):

    login_url = 'accounts:login'

    def dispatch(self, request, *args, **kwargs):

        user = request.user

        if not user.is_authenticated:

            messages.error(request,"You must logged in to access this page.")
            return redirect('accounts:login')
        if hasattr(user, 'role'):

            if user.role != 'customer':

                raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)