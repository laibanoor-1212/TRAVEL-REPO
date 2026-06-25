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
from packages.models import Package
from django.contrib.auth.decorators import user_passes_test
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
def review_agent(request, pk):
    profile = get_object_or_404(AgentKYC, pk=pk)

    if request.method == "POST":
        action = request.POST.get('action')
        comment = request.POST.get('comment')

        profile.admin_comment = comment

        if action == 'approve':
            profile.kyc_status = 'approved'
            profile.rejected_fields = ""  # Clear fields on approval
            messages.success(request, "KYC approved successfully.")
        
        elif action == 'reject':
            profile.kyc_status = 'rejected'
            messages.error(request, "KYC has been rejected.")
            
        elif action == 'rollback':
            profile.kyc_status = 'rollback'
            # Checkboxes se selected fields ki list lein
            selected_fields = request.POST.getlist('reject_fields_list')
            # Comma-separated string bana kar save karein (e.g., "agency_name,ntn_doc")
            profile.rejected_fields = ",".join(selected_fields)
            messages.warning(request, "KYC status set to rollback with selected fields.")

        profile.save()
        return redirect('adminpanel:admin_dashboard') # Apne admin dashboard ka route dein

    return render(request, 'adminpanel/review_agent.html', {'profile': profile})
def admin_logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('adminpanel:admin_login')
def is_platform_admin(user):
    return user.is_authenticated and user.is_superuser

@user_passes_test(is_platform_admin)
def admin_packages(request):
    # 'is_active' ki jagah 'status' field use kar rahe hain
    # Agar aap active status ke liye 'approved' use karti hain to 'active' ko change kar lein
    active_packages = Package.objects.filter(status='active').order_by('-id')
    
    # Blocked packages ke liye status='blocked' filter karenge
    blocked_packages = Package.objects.filter(status='blocked').order_by('-id')
    
    context = {
        'active_packages': active_packages,
        'blocked_packages': blocked_packages,
    }
    return render(request, 'adminpanel/admin_packages.html', context)


@user_passes_test(is_platform_admin)
def block_package(request, pkg_id):
    """Package ko block karne ke liye"""
    package = get_object_or_404(Package, id=pkg_id)
    package.status = 'blocked'
    package.save()
    messages.warning(request, f"Package #{package.id} has been blocked successfully.")
    return redirect('adminpanel:admin_packages')


@user_passes_test(is_platform_admin)
def unblock_package(request, pkg_id):
    """Blocked package ko dobara active karne ke liye"""
    package = get_object_or_404(Package, id=pkg_id)
    package.status = 'active'
    package.save()
    messages.success(request, f"Package #{package.id} is now live again.")
    return redirect('adminpanel:admin_packages')


@user_passes_test(is_platform_admin)
def remove_package(request, pkg_id):
    """Package ko permanently delete karne ke liye"""
    package = get_object_or_404(Package, id=pkg_id)
    package.delete()
    messages.error(request, "Package has been permanently removed from the system.")
    return redirect('adminpanel:admin_packages')