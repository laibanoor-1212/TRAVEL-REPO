from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser

class CustomUserRegistrationForm(UserCreationForm):
   
    ROLE_CHOICES = (
        ("user", "User"),
        ("stakeholder", "Stakeholder"),
    )

    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}) 
    )

    class Meta:
        model = CustomUser
        # UserCreationForm ke default fields aur hamare kstom fields
        fields = ("first_name", "last_name", "email", "role","phone_number", "agency_name")

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already exists")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        
       
        user.username = self.cleaned_data["email"]
        user.email = self.cleaned_data["email"]
        user.role = self.cleaned_data["role"]
        user.phone_number = self.cleaned_data.get("phone_number")
        user.agency_name = self.cleaned_data.get("agency_name")

      
        if user.role == "stakeholder":
            user.is_approved = False
            user.is_staff = False 
        else:
            user.is_approved = True

        if commit:
            user.save()
        return user