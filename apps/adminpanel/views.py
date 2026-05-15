from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from django.core.mail import send_mail
from .decorators import admin_required 
from accounts.models import CustomUser
from django.conf import settings
from urllib.parse import quote, unquote

User = get_user_model()

def admin_login_view(request):
    
    # Agar pehle se login hai
    if request.user.is_authenticated and (
        request.user.is_superuser or request.user.role == 'admin'
    ):
        return redirect('admin_dashboard')

    if request.method == 'POST':

        email = request.POST.get('email')
        password = request.POST.get('password')

        try:
            # Email se user nikaalo
            user_obj = User.objects.get(email=email)

            # Username se authenticate karo
            user = authenticate(
                request,
                username=user_obj.username,
                password=password
            )

        except User.DoesNotExist:
            user = None

        if user is not None:

            # Admin ya superuser check
            if user.is_superuser or user.role == 'admin':

                login(request, user)
                messages.success(request, "Welcome to Safar-e-Haram Admin Panel!")
                return redirect('admin_dashboard')

            else:
                messages.error(request, "Access denied.")

        else:
            messages.error(request, "Invalid email or password!")

    return render(request, 'adminpanel/admin_login.html')

def admin_forget_password(request):
    
    if request.method == "POST":

        email = request.POST.get("email")
        user = User.objects.filter(email=email, role='admin').first()

        if user:

            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)

            reset_link = request.build_absolute_uri(
                f"/adminpanel/reset_confirm/{uid}/{token}/"
            )

            msg_html = render_to_string(
                "adminpanel/email/reset_password_email.html",
                {"user": user, "reset_link": reset_link}
            )

            send_mail(
                "Password Reset",
                "Reset your password",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=msg_html,
            )

            messages.success(request, "Reset link sent!")
            return redirect("adminpanel:admin_login")

    return render(request, "adminpanel/admin_forget_password.html")




def admin_reset_password_confirm(request, uidb64, token):
    
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)

    except Exception:
        user = None

    if user and default_token_generator.check_token(user, token):

        if request.method == "POST":
            password = request.POST.get("password")
            confirm = request.POST.get("confirm_password")

            if password == confirm:
                user.set_password(password)
                user.save()
                messages.success(request, "Password reset successful")
                return redirect("adminpanel:admin_login")

        return render(request, "adminpanel/reset_confirm.html")

    return render(request, "adminpanel/forget_password_invalid.html")

@admin_required
def admin_dashboard_view(request):
    pending_agents = User.objects.filter(role='agent', is_verified=False)
    total_users = User.objects.count()
    total_agents = User.objects.filter(role='agent').count()
    verified_agents = User.objects.filter(role='agent', is_verified=True).count()

    context = {
        'pending_agents': pending_agents,
        'total_users': total_users,
        'total_agents': total_agents,
        'verified_agents': verified_agents,
    }
    return render(request, 'adminpanel/dashboard.html', context)


@admin_required
def approve_agent_view(request, user_id):
    agent = get_object_or_404(User, id=user_id, role='agent')
    agent.is_verified = True
    agent.save()
    messages.success(request, f"Agent {agent.username} has been approved.")
    return redirect('admin_dashboard')

@admin_required
def reject_agent_view(request, user_id):
    agent = get_object_or_404(User, id=user_id, role='agent')
    agent.delete() 
    messages.warning(request, f"Agent {agent.username} has been rejected.")
    return redirect('admin_dashboard')
def admin_logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('admin_login')