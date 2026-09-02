from django import forms
from .models import SystemSetting
from .models import GuidePage
class SystemPreferenceForm(forms.ModelForm):
    class Meta:
        model = SystemSetting
        fields = ['primary_currency', 'timezone']
        widgets = {
            'primary_currency': forms.Select(attrs={'class': 'form-control'}),
            'timezone': forms.Select(attrs={'class': 'form-control'}),
        }



class GuidePageForm(forms.ModelForm):
    class Meta:
        model = GuidePage
        fields = ['title', 'page_slug', 'banner_image', 'content', 'is_published']


