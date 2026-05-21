from django import forms
from .models import AgentKYC


class KYCAgentForm(forms.ModelForm):

    class Meta:

        model = AgentKYC

        exclude = (
            'user',
            'kyc_status',
            'admin_comment',
            'submitted_at',
            'updated_at',
        )