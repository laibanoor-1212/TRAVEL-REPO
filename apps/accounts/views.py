from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from .models import CustomUser
from django.utils.http import urlsafe_base64_decode,urlsafe_base64_encode
from django.utils.encoding import force_str, force_bytes
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator
from django.contrib.auth.forms import PasswordResetForm,SetPasswordForm
from .forms import CustomUserRegistrationForm
from django.contrib.auth import authenticate, login as auth_login
from django.urls import reverse
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import get_user_model
User = get_user_model()


def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_superuser or request.user.is_staff:
            return redirect('adminpanel:dashboard')
        elif getattr(request.user, 'role', None) == 'stakeholder':
            return redirect('stakeholder:KYC')
        else:
            return redirect('customers:user_dashboard')

    if request.method == 'POST':
        email_or_username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(
            request, username=email_or_username, password=password
        )

        if user is not None:
            if not user.is_active:
                messages.error(
                    request,
                    'Your account is not activated yet. Please check your email for the activation link.',
                )
                return render(request, 'accounts/login.html')

            auth_login(request, user)
            messages.success(request, 'Login Successful!')

            if user.is_superuser or user.is_staff:
                return redirect('adminpanel:dashboard')
            elif getattr(user, 'role', None) == 'stakeholder':
                return redirect('stakeholder:KYC')
            else:
                return redirect('customers:user_dashboard')
        else:
            messages.error(request, 'Invalid Username/Email or Password.')

    return render(request, 'accounts/login.html')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('base:home')

    if request.method == 'POST':
        form = CustomUserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()

            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)

            relative_url = reverse(
                'accounts:activate', kwargs={'uidb64': uid, 'token': token}
            )
            activation_link = request.build_absolute_uri(relative_url)

            mail_subject = 'Safar-e-Haram - Verify Your Account'
            html_message = f"""
            <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
                <h2 style="color: #1a5f7a; text-align: center;">Welcome to Safar-e-Haram!</h2>
                <p>Hello <strong>{user.first_name or user.username}</strong>,</p>
                <p>Thank you for registering with Safar-e-Haram. Please verify your account to get started.</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{activation_link}" style="background-color: #1a5f7a; color: #ffffff; padding: 12px 25px; text-decoration: none; font-size: 16px; border-radius: 5px; display: inline-block; font-weight: bold;">Activate My Account</a>
                </div>
                
                <p style="font-size: 13px; color: #666;">If the button above does not work, copy and paste this link into your browser:</p>
                <p style="font-size: 13px; word-break: break-all;"><a href="{activation_link}">{activation_link}</a></p>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                <p style="font-size: 12px; color: #888; text-align: center;">If you did not register for this account, please ignore this email.</p>
            </div>
            """

            plain_message = strip_tags(html_message)

            try:
                send_mail(
                    subject=mail_subject,
                    message=plain_message,
                    from_email=getattr(
                        settings, 'DEFAULT_FROM_EMAIL', settings.EMAIL_HOST_USER
                    ),
                    recipient_list=[user.email],
                    html_message=html_message, 
                    fail_silently=False,
                )
                messages.success(
                    request,
                    'Registration successful! We have sent an activation link to your email. Please verify before logging in.',
                )
            except Exception as e:
                messages.error(
                    request,
                    f'Failed to send activation email. Error: {str(e)}',
                )

            return redirect('accounts:login')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        initial_role = request.GET.get('role', 'user')
        form = CustomUserRegistrationForm(initial={'role': initial_role})

    return render(request, 'accounts/register.html', {'form': form})


def activate_account(request, uidb64, token):
    User = get_user_model()
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if not user.is_active:
            user.is_active = True
            user.save()
            messages.success(
                request,
                'Your account has been successfully activated! You can now log in.',
            )
        else:
            messages.info(
                request, 'Your account is already activated. Please log in.'
            )
        return redirect('accounts:login')
    else:
        messages.error(
            request,
            'The activation link is invalid, expired, or has already been used.',
        )
        return redirect('accounts:login')
def logout_view(request):
    logout(request)
    messages.success(request, "Logout successful!")
    return redirect('accounts:login')

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
            return redirect("accounts:login")
        else:
            messages.error(request,"No user found with this email.")
    return render( request,"accounts/forget_password.html" )
def reset_password_confirm(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is None or not default_token_generator.check_token(user, token):
        return render(request, "accounts/forget_password_invalid.html")
    if request.method == 'POST':
        new_password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if not new_password or not confirm_password:
            messages.error(request, "Please fill in all fields.")
        elif new_password != confirm_password:
            messages.error(request, "New password and confirm password do not match!")
        else:
            try:
                validate_password(new_password, user=user)
                user.set_password(new_password)
                user.save()
                return render(request, "accounts/forget_reset_confirm.html")
                
            except ValidationError as e:
                for error in e.messages:
                    messages.error(request, error)
    return render(request, "accounts/password_reset_confirm.html")
    

def is_platform_admin(user):
    return user.is_authenticated and user.is_superuser

@user_passes_test(is_platform_admin)
def admin_manage_users(request):
    base_users = CustomUser.objects.exclude(is_superuser=True).exclude(role='admin').order_by('-date_joined')
    
    active_tab = request.GET.get('tab', 'all')
    if active_tab == 'active':
        users_list = base_users.filter(is_active=True, is_approved=True)
    elif active_tab == 'deactivated':
        users_list = base_users.filter(is_active=False, is_approved=True)
    elif active_tab == 'suspended':
       
        users_list = base_users.filter(is_active=False, is_approved=False).exclude(agency_name="BANNED_PERMANENTLY")
    elif active_tab == 'perm_suspended':
      
        users_list = base_users.filter(agency_name="BANNED_PERMANENTLY")
    else:
        users_list = base_users 
        
    search_query = request.GET.get('search', '')
    if search_query:
        users_list = users_list.filter(email__icontains=search_query)
    counts = {
        'all': base_users.count(),
        'active': base_users.filter(is_active=True, is_approved=True).count(),
        'deactivated': base_users.filter(is_active=False, is_approved=True).count(),
        'suspended': base_users.filter(is_active=False, is_approved=False).exclude(agency_name="BANNED_PERMANENTLY").count(),
        'perm_suspended': base_users.filter(agency_name="BANNED_PERMANENTLY").count(),
    }
        
    paginator = Paginator(users_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'users': page_obj,
        'search_query': search_query,
        'active_tab': active_tab,
        'counts': counts,
        'total_users': users_list.count(),
    }
    return render(request, 'accounts/admin_users_list.html', context)


@user_passes_test(is_platform_admin)
def change_user_status(request, user_id, status_action):
    user = get_object_or_404(CustomUser, id=user_id)
    current_tab = request.GET.get('tab', 'all')
    
    if status_action == 'deactivate':
        user.is_active = False
        user.is_approved = True
        messages.success(request, f"Account {user.email} has been deactivated.")
    elif status_action == 'activate':
        user.is_active = True
        user.is_approved = True
        if user.agency_name == "BANNED_PERMANENTLY":
            user.agency_name = "" 
        messages.success(request, f"Account {user.email} has been fully activated.")
    elif status_action == 'suspend':
        # Temporary Suspend logic
        user.is_active = False
        user.is_approved = False  
        messages.warning(request, f"Account {user.email} has been temporarily suspended.")
    elif status_action == 'perm_suspend':
        # Permanent Suspend logic
        user.is_active = False
        user.is_approved = False
        user.agency_name = "BANNED_PERMANENTLY"  
        messages.error(request, f"Account {user.email} has been permanently blacklisted/suspended.")
        
    user.save()
    return redirect(f"/accounts/admin-dashboard/users/?tab={current_tab}")
