from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from django.core.mail import send_mail
from stakeholder.models import AgentKYC
from django.conf import settings
User = get_user_model()

def admin_login_view(request):
    
    # Agar pehle se login hai
    if request.user.is_authenticated and (
        request.user.is_superuser or request.user.role == 'admin'
    ):
        return redirect('adminpanel:admin_dashboard')

    if request.method == 'POST':

        email = request.POST.get('email')
        password = request.POST.get('password')

        try:
         
            user_obj = User.objects.get(email=email)

          
            user = authenticate(
                request,
                username=user_obj.username,
                password=password
            )

        except User.DoesNotExist:
            user = None

        if user is not None:
            if user.is_superuser or user.role == 'admin':

                login(request, user)
                messages.success(request, "Welcome to Safar-e-Haram Admin Panel!")
                return redirect('adminpanel:admin_dashboard')

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

def admin_dashboard(request):
    return render(request,'adminpanel/admin_dashboard.html')
def agent_requests(request):
    pending_count = AgentKYC.objects.filter(
        kyc_status='pending'
    ).count()

    rollback_count = AgentKYC.objects.filter(
        kyc_status='rollback'
    ).count()

    rejected_count = AgentKYC.objects.filter(
        kyc_status='rejected'
    ).count()

    approved_count = AgentKYC.objects.filter(
        kyc_status='approved'
    ).count()

    requests = AgentKYC.objects.all().order_by(
        '-submitted_at'
    )
    return render(
        request,
        'adminpanel/agent_requests.html',
        {
            'pending_count': pending_count,
            'rollback_count': rollback_count,
            'rejected_count': rejected_count,
            'approved_count': approved_count,
            'requests': requests,
        }
    )
def review_agent(request, profile_id):
    profile = get_object_or_404(AgentKYC, id=profile_id)

    if request.method == 'POST':
        action = request.POST.get('action')
        comment = request.POST.get('comment')

        # Comment ko pehle hi assign kar diya
        profile.admin_comment = comment

        if action == 'approve':
            profile.kyc_status = 'approved'
            messages.success(request, f"Agent application approved successfully!")

        elif action == 'rollback':
            profile.kyc_status = 'rollback'
            messages.warning(request, f"Application sent back for correction (Rollback).")
            
        elif action == 'reject':
            profile.kyc_status = 'rejected'
            messages.error(request, f"Agent application has been rejected.")

        # Data ko database mein save kiya
        profile.save()
        return redirect('adminpanel:agent_requests')

    return render(request, 'adminpanel/review_agent.html', {
        'profile': profile
    })
def admin_logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('adminpanel:admin_login')