import re
import dns.resolver
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from .models import CustomUser


class CustomUserRegistrationForm(UserCreationForm):

    ROLE_CHOICES = (
        ("user", "User"),
        ("stakeholder", "Stakeholder"),
    )

    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    class Meta:
        model = CustomUser
        fields = (
            "first_name",
            "last_name",
            "email",
            "role",
            "phone_number",
            "agency_name",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != "role":
                field.widget.attrs.update({"class": "form-control"})

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not email:
            raise forms.ValidationError("Email address is required.")

        email = email.lower().strip()

        # 1. Username Minimum Length Check (blocks short emails like 'ee@gmail.com')
        username_part = email.split("@")[0]
        if len(username_part) < 3:
            raise forms.ValidationError(
                "Email username before @ must be at least 3 characters long."
            )

        # 2. Strict Format Check
        validator = EmailValidator(
            message="Please enter a valid email address (e.g. name@example.com)."
        )
        try:
            validator(email)
        except ValidationError:
            raise forms.ValidationError(
                "Invalid email format. Please enter a proper email address."
            )

        # 3. Block Disposable / Fake Email Domains
        disposable_domains = {
            "tempmail.com", "mailinator.com", "10minutemail.com", "guerrillamail.com",
            "sharklasers.com", "dispostable.com", "yopmail.com", "trashmail.com",
            "mail.com", "email.com", "temp-mail.org", "getnada.com", "throwawaymail.com",
            "fakeinbox.com", "guerrillamail.info", "grr.la", "guerrillamail.biz",
            "guerrillamail.de", "guerrillamail.net", "guerrillamail.org", "pokemail.net",
            "spam4.me", "bccto.me", "chacuo.net"
        }
        domain = email.split("@")[-1]
        if domain in disposable_domains:
            raise forms.ValidationError(
                "Temporary or disposable email addresses are not allowed."
            )

        # 4. Real Domain MX Record Lookup
        try:
            resolver = dns.resolver.Resolver()
            resolver.timeout = 2
            resolver.lifetime = 2
            resolver.resolve(domain, "MX")
        except (
            dns.resolver.NoAnswer,
            dns.resolver.NXDOMAIN,
            dns.resolver.NoNameservers,
        ):
            raise forms.ValidationError(
                "This email domain does not exist or cannot receive emails."
            )
        except Exception:
            pass

        # 5. Duplicate Email & Username Check
        if (
            CustomUser.objects.filter(email__iexact=email).exists()
            or CustomUser.objects.filter(username__iexact=email).exists()
        ):
            raise forms.ValidationError("This email is already registered.")

        return email

    def clean_phone_number(self):
        phone = self.cleaned_data.get("phone_number")
        role = self.cleaned_data.get("role")

        if role == "stakeholder" or phone:
            if not phone:
                raise forms.ValidationError("Phone number is required for agents.")

            # Spaces ya brackets clear karein
            phone = re.sub(r'[\s\-\(\)]', '', phone.strip())
            
            # Accepts: Local Pakistani (03001234567) OR International Format (+966512345678, +923001234567)
            global_phone_regex = r"^(\+?[1-9]\d{7,14}|03\d{9})$"

            if not re.match(global_phone_regex, phone):
                raise forms.ValidationError(
                    "Please enter a valid phone number (e.g. 03001234567 or +966512345678)."
                )

        return phone

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")
        agency_name = cleaned_data.get("agency_name")

        # Directly field ke andar error throw hoga
        if role == "stakeholder":
            if not agency_name or not agency_name.strip():
                self.add_error(
                    "agency_name", "Agency name is required for stakeholders."
                )
            else:
                agency_name = agency_name.strip()
                if len(agency_name) < 3:
                    self.add_error(
                        "agency_name", "Agency name must be at least 3 characters long."
                    )
                elif agency_name.isdigit():
                    self.add_error(
                        "agency_name", "Agency name cannot consist only of numbers."
                    )

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)

        email = self.cleaned_data["email"]
        user.username = email
        user.email = email
        user.role = self.cleaned_data["role"]
        
        phone = self.cleaned_data.get("phone_number")
        if phone:
            user.phone_number = re.sub(r'[\s\-\(\)]', '', phone.strip())

        agency_name = self.cleaned_data.get("agency_name")
        user.agency_name = agency_name.strip() if agency_name else None

        if user.role == "stakeholder":
            user.is_approved = False
            user.is_staff = False
        else:
            user.is_approved = True

        if commit:
            user.save()
        return user