from django import forms
from .models import Package

class PackageForm(forms.ModelForm):
    class Meta:
        model = Package
        fields = [
            'name',
            'package_type',
            'tier',
            'country',
            'city',
            'price',
            'duration_days',
            'total_seats',
            'application_deadline',
            'description',
            'status',
        ]

        widgets = {
            'application_deadline': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 5}),
        }