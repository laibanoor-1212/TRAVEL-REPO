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
        widget=forms.HiddenInput()
    )

    username = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )

    class Meta:
        model = CustomUser

        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "role",
            "password1",
            "password2",
        ]

    def clean_email(self):

        email = self.cleaned_data.get("email")

        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already exists")

        return email

    def save(self, commit=True):

        user = super().save(commit=False)

        user.username = self.cleaned_data["email"]

        user.role = self.cleaned_data["role"]

        if user.role == "stakeholder":
            user.is_approved = False
        else:
            user.is_approved = True

        if commit:
            user.save()

        return user