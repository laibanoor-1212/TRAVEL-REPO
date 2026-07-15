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
from django.utils.encoding import force_str
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator
from django.contrib.auth.forms import PasswordResetForm,SetPasswordForm
from .forms import CustomUserRegistrationForm
from django.contrib.auth import authenticate, login as auth_login
from django.contrib import messages

def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_superuser or request.user.is_staff:
                return redirect('adminpanel:admin_login') 
        elif request.user.role == 'stakeholder':
            return redirect('stakeholder:KYC')
        else:
            return redirect('customers:user_dashboard')

    if request.method == "POST":
       
        email_or_username = request.POST.get('username') 
        password = request.POST.get('password')
        user = authenticate(request, username=email_or_username, password=password)

        if user is not None:
            auth_login(request, user)
            
            messages.success(request, "Login Successful!")
            if user.is_superuser or user.is_staff:
                    return redirect('adminpanel:admin_login') 
            elif user.role == 'stakeholder':
                return redirect('stakeholder:KYC')
            else:
                return redirect('customers:user_dashboard')
           
        else:
            messages.error(request, "Invalid Username/Email or Password.")
            
    return render(request, 'accounts/login.html') 

def register_view(request): 
    if request.method == 'POST':
        form = CustomUserRegistrationForm(request.POST)
        if form.is_valid():

            user = form.save(commit=False)
            user.save()
            if user.role == 'stakeholder':
                request.session['stakeholder_id'] = user.id
                messages.success(request, "Stakeholder account created successfully. Please submit your docs.")
                return redirect('stakeholder:KYC')
 
            else:
                login(request, user,backend='django.contrib.auth.backends.ModelBackend')
                messages.success(request, "User account created successfully")
                return redirect('customers:user_dashboard')

    else:
        form = CustomUserRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


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
    

def is_platform_admin(user):
    return user.is_authenticated and user.is_superuser

@user_passes_test(is_platform_admin)
def admin_manage_users(request):
    base_users = CustomUser.objects.exclude(is_superuser=True).exclude(role='admin').order_by('-date_joined')
    
    active_tab = request.GET.get('tab', 'all')
    
    # 4 Alag Alag tab status ki filtration logic
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
        
    # Counters object updates for top navigation indicators
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