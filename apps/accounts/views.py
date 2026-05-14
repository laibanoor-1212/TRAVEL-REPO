from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from .models import CustomUser
from django.utils.http import urlsafe_base64_decode,urlsafe_base64_encode
from django.utils.encoding import force_str
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm,SetPasswordForm
from .forms import CustomUserRegistrationForm

def register_view(request): 
    if request.method == 'POST':

        form = CustomUserRegistrationForm(request.POST)

        if form.is_valid():

            user = form.save(commit=False)
            user.save()

            # stakeholder  go to login
            if user.role == 'stakeholder':
                messages.success(request, "Stakeholder account created successfully. Please submit your docs.")
                return redirect('create_profile')

            # user  auto login 
            else:
                login(request, user)
                messages.success(request, "User account created successfully")
                return redirect('user_dashboard')

    else:
        form = CustomUserRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})

def login_view(request):
    
    if request.method == 'POST':

        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:

            login(request, user)

            if user.role == 'stakeholder':

                if not user.is_approved:
                    logout(request)
                    messages.error(request, "Your stakeholder account is pending approval")
                    return redirect('login')

                else:
                    return redirect('stakeholder_dashboard')

            else:
                return redirect('user_dashboard')

        else:
            messages.error(request, "Invalid credentials!")

    return render(request, 'accounts/login.html')

def logout_view(request):
    logout(request)
    messages.success(request, "Logout successful!")
    return redirect('login')

def forget_password(request):
    if request.method == "POST":
        email = request.POST.get("email")
        users = CustomUser.objects.filter(email=email)
        if users.exists():
            for user in users:
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                reset_link = (f"{request.scheme}://" f"{request.get_host()}" f"/auth/reset-confirm/{uid}/{token}/")
                email_template = "accounts/email/reset_password_email.html"

                parameters = {
                    "user": user,
                    "reset_link": reset_link,
                }
                msg_html = render_to_string(email_template,parameters)
                subject = "Password Reset Request"
                send_mail(
                    subject,
                    "Please reset email password using the link provided below",
                    settings.EMAIL_HOST_USER,
                    [user.email],
                    fail_silently=False,
                    html_message=msg_html,
                )
            messages.success(request,"Reset link sent to your email.")
            return redirect("login")
        else:
            messages.error(request,"No user found with this email.")
    return render( request,"accounts/forget_password.html" )



def reset_password_confirm(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None
    if user is not None and default_token_generator.check_token(user, token):

        if request.method == "POST":
            new_password = request.POST.get("password")
            confirm_password = request.POST.get("confirm_password")
            if new_password == confirm_password:

                user.set_password(new_password)
                user.save()

                messages.success(request, "Password reset successfully!")
                return redirect("login")

            else:
                messages.error(request, "New password and confirm password do not match!")

        return render(request, "accounts/reset_password_confirm.html")

    else:
        return render(request, "accounts/forget_password_invalid.html")
def create_profile(request):
    return render(request, 'accounts/create_profile.html')