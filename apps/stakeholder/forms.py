from django import forms
from .models import AgentKYC

class KYCAgentForm(forms.ModelForm):
    class Meta:
        model = AgentKYC
       
        exclude = ['user', 'kyc_status', 'admin_comment', 'submission_count', 'rejected_fields']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
       
        if self.instance and self.instance.kyc_status == 'rollback':
         
            allowed_fields = [f.strip() for f in self.instance.rejected_fields.split(',') if f.strip()]
            
          
            for field_name in self.fields:
                if field_name not in allowed_fields:
                    self.fields[field_name].disabled = True
                  
                    self.fields[field_name].widget.attrs['class'] = 'form-control locked-field'