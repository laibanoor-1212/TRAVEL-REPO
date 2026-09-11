from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model, update_session_auth_hash
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from stakeholder.models import AgentKYC
from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from packages.models import Package, PackageType
from customers.models import CustomerProfile 
from bookings.models import Bookings, BookingStatusHistory
from notifications.models import Notification
from .models import Complaint, SystemSetting, GuidePage
from payments.models import EscrowTransaction, CommissionSetting, PaymentRelease, Payment, PaymentProof, PaymentStatusLog, PaymentStatus
from apps.accounts.models import CustomUser
import json
from .decorators import admin_required
from django.views.decorators.http import require_POST
from django.db.models import Sum, Count, Q
from payments import services
from decimal import Decimal
from django.http import HttpResponse, JsonResponse
from django.core.serializers import serialize
from django.core.exceptions import ValidationError
from .forms import SystemPreferenceForm
from django.db.models import ProtectedError,F
from django.utils import timezone

# Utils Email Module Imports
from utils.emails import (
    send_password_change_email,
    send_booking_status_email,
    
)

def is_admin_user(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser or getattr(user, 'role', '') == 'admin')

def is_platform_admin(user):
    return user.is_authenticated and user.is_superuser

User = get_user_model()

def admin_login_view(request):
    if request.user.is_authenticated and (
        request.user.is_superuser or getattr(request.user, 'role', '') == 'admin'
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
            if user.is_superuser or getattr(user, 'role', '') == 'admin':
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

            from django.core.mail import send_mail
            send_mail(
                "Password Reset - Safar-e-Haram Admin",
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

                send_password_change_email(user)

                messages.success(request, "Password reset successful")
                return redirect("adminpanel:admin_login")

        return render(request, "adminpanel/reset_confirm.html")

    return render(request, "adminpanel/forget_password_invalid.html")

@admin_required
def admin_dashboard(request):
    stakeholders_qs = CustomUser.objects.filter(role='stakeholder')
    pending_agents = stakeholders_qs.filter(is_approved=False).count()
    verified_agents = stakeholders_qs.filter(is_approved=True).count()
    total_pilgrims = CustomUser.objects.filter(role='customer').count()
    active_packages = Package.objects.filter(status='active').count()
    pending_bookings = Bookings.objects.filter(status='pending').count()
    completed_bookings = Bookings.objects.filter(status='completed').count()
    escrow_agg = EscrowTransaction.objects.filter(
        status=EscrowTransaction.Status.HELD
    ).aggregate(Sum('held_amount'))
    total_escrow = escrow_agg['held_amount__sum'] or 0
    revenue_agg = Payment.objects.filter(
        payment_status=PaymentStatus.RELEASED
    ).aggregate(Sum('amount'))
    total_revenue = revenue_agg['amount__sum'] or 0
    context = {
        'pending_agents': pending_agents,
        'verified_agents': verified_agents,
        'total_pilgrims': total_pilgrims,
        'active_packages': active_packages,
        'pending_bookings': pending_bookings,
        'completed_bookings': completed_bookings,
        'total_escrow': total_escrow,
        'total_revenue': total_revenue,
        'stakeholders_qs': stakeholders_qs,
    }

    return render(request, 'adminpanel/admin_dashboard.html', context)

@admin_required
def agent_requests(request):
    pending_count = AgentKYC.objects.filter(kyc_status='pending').count()
    rollback_count = AgentKYC.objects.filter(kyc_status='rollback').count()
    rejected_count = AgentKYC.objects.filter(kyc_status='rejected').count()
    approved_count = AgentKYC.objects.filter(kyc_status='approved').count()

    requests = AgentKYC.objects.all().order_by('-submitted_at')
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

@admin_required
def review_agent(request, pk):
    profile = get_object_or_404(AgentKYC, pk=pk)

    if request.method == "POST":
        action = request.POST.get('action')
        comment = request.POST.get('comment', '')

        profile.admin_comment = comment

        if action == 'approve':
            profile.kyc_status = 'approved'
            profile.rejected_fields = "" 
            if hasattr(profile.user, 'is_approved'):
                profile.user.is_approved = True
                profile.user.save()
            messages.success(request, "KYC approved successfully.")
        
        elif action == 'reject':
            profile.kyc_status = 'rejected'
            if hasattr(profile.user, 'is_approved'):
                profile.user.is_approved = False
                profile.user.save()
            messages.error(request, "KYC has been rejected.")
            
        elif action == 'rollback':
            profile.kyc_status = 'rollback'
            selected_fields = request.POST.getlist('reject_fields_list')
            profile.rejected_fields = ",".join(selected_fields)
            if hasattr(profile.user, 'is_approved'):
                profile.user.is_approved = False
                profile.user.save()
            messages.warning(request, "KYC status set to rollback with selected fields.")

        profile.save()

        # Email notification to agent
        if profile.user and getattr(profile.user, 'email', None):
            send_kyc_status_email(profile.user, profile.kyc_status, comment)

        return redirect('adminpanel:admin_dashboard') 

    return render(request, 'adminpanel/review_agent.html', {'profile': profile})

@admin_required
def admin_logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('adminpanel:admin_login')

@user_passes_test(is_platform_admin)
@admin_required
def admin_packages(request):
    today = timezone.now().date()
    date_filter = Q(application_deadline__gte=today) if hasattr(Package, 'application_deadline') else Q(end_date__gte=today)
    seat_filter = Q(booked_seats__lt=F('total_seats')) if hasattr(Package, 'booked_seats') else Q(seats_left__gt=0)

    active_packages = Package.objects.filter(
        Q(status='active') & date_filter & seat_filter
    ).order_by('-id')
    blocked_packages = Package.objects.exclude(
        id__in=active_packages.values_list('id', flat=True)
    ).order_by('-id')

    context = {
        'active_packages': active_packages,
        'blocked_packages': blocked_packages,
        'today': today,
    }
    return render(request, 'adminpanel/admin_packages.html', context)


@user_passes_test(is_platform_admin)
@admin_required
def block_package(request, pkg_id):
    package = get_object_or_404(Package, id=pkg_id)
    package.status = 'blocked'
    package.save()

    agent = getattr(package, 'agent', None) or getattr(package, 'agency', None)
    if agent and 'send_package_status_email' in globals():
        send_package_status_email(agent, package, 'blocked')

    messages.warning(request, f"Package #{package.id} has been blocked successfully.")
    return redirect('adminpanel:admin_packages')


@user_passes_test(is_platform_admin)
@admin_required
def unblock_package(request, pkg_id):
    package = get_object_or_404(Package, id=pkg_id)
    package.status = 'active'
    package.save()

    agent = getattr(package, 'agent', None) or getattr(package, 'agency', None)
    if agent and 'send_package_status_email' in globals():
        send_package_status_email(agent, package, 'active')

    messages.success(request, f"Package #{package.id} is now live again.")
    return redirect('adminpanel:admin_packages')

@user_passes_test(is_platform_admin)
@admin_required
def remove_package(request, pkg_id):
    package = get_object_or_404(Package, id=pkg_id)
    
    if hasattr(package, 'is_active'):
        package.is_active = False
    if hasattr(package, 'status'):
        package.status = 'inactive' 
    package.save()
    agent = getattr(package, 'agent', None) or getattr(package, 'agency', None)
    if agent and 'send_package_status_email' in globals():
        send_package_status_email(agent, package, 'deactivated')

    messages.warning(request, f"Package '{package.title if hasattr(package, 'title') else package.id}' has been deactivated (soft removed). Connected bookings remain safe.")
    return redirect('adminpanel:admin_packages')
@admin_required
def admin_customer(request):
    customers = CustomerProfile.objects.all().order_by('-id')
    context = {'customers': customers}
    return render(request, 'adminpanel/admin_customers.html', context)

@admin_required
def customer_detail(request, profile_id):
    customer_profile = get_object_or_404(CustomerProfile, id=profile_id)
    selected_packages = customer_profile.interested_packages.split(',') if customer_profile.interested_packages else []
    
    context = {
        'customer': customer_profile,
        'selected_packages': selected_packages
    }
    return render(request, 'adminpanel/admin_customer_details.html', context)

@admin_required
@login_required
def admin_bookings(request):
    view_id = request.GET.get('view_id')
    payment_id = request.GET.get('payment_id')
    all_bookings = Bookings.objects.select_related(
        'user', 
        'package'
    ).prefetch_related(
        'customer_profiles',  
        'status_history',    
        'documents'           
    ).all()

    selected_booking_details = None
    selected_booking_payment = None

    if view_id:
        selected_booking_details = get_object_or_404(
            Bookings.objects.select_related('user', 'package').prefetch_related('customer_profiles', 'documents'),
            id=view_id
        )

    if payment_id:
        selected_booking_payment = get_object_or_404(
            Bookings.objects.select_related('user', 'package'),
            id=payment_id
        )

    context = {
        'bookings': all_bookings,
        'selected_booking_details': selected_booking_details,
        'selected_booking_payment': selected_booking_payment,
    }

    return render(request, 'adminpanel/admin_booking.html', context)

@admin_required
def update_booking_status(request, booking_id):
    if not request.user.is_authenticated:
        return redirect('/accounts/login/')
        
    if not request.user.is_staff:
        messages.error(request, "You do not have authority to access this.")
        return redirect('customers:user_dashboard')
        
    if request.method == 'POST':
        booking = get_object_or_404(Bookings, id=booking_id)
        old_status = booking.status
        new_status = request.POST.get('status')
        valid_statuses = [choice[0] for choice in Bookings.STATUS_CHOICES]
        
        if new_status in valid_statuses:
            booking.status = new_status
            booking.save()
            BookingStatusHistory.objects.create(
                booking=booking,
                old_status=old_status,
                new_status=new_status,
                changed_by=request.user,
                remarks="Status updated via Admin Control Center."
            )

            # Customer & Agent Email Notifications
            if booking.user:
                send_booking_status_email(booking.user, booking, new_status)
            if hasattr(booking.package, 'agent') and booking.package.agent:
                send_booking_status_email(booking.package.agent, booking, new_status)
            
            messages.success(request, f"Booking #{booking.booking_id} status successfully set to '{booking.get_status_display()}'")
        else:
            messages.error(request, "Invalid status selected.")
            
    return redirect('adminpanel:admin_bookings')

@admin_required
def admin_complaints(request):
    if request.method == "POST":
        complaint_id = request.POST.get("complaint_id")
        new_status = request.POST.get("status")
        
        if complaint_id and new_status:
            complaint = get_object_or_404(Complaint, id=complaint_id)
            complaint.status = new_status
            complaint.save()

            if complaint.user:
                send_complaint_status_email(complaint.user, complaint, new_status)

            messages.success(request, f"Complaint #SH-C-{complaint.id} status updated to '{complaint.get_status_display()}' successfully.")
            return redirect('adminpanel:admin_complaints')

    complaints = Complaint.objects.select_related('user').order_by('-created_at')
    return render(request, 'adminpanel/admin_complaint.html', {'complaints': complaints})

@admin_required
def admin_payments_list(request):
    payments = Payment.objects.all().order_by('-id')
    method_filter = request.GET.get('method', '').strip()
    status_filter = request.GET.get('status', '').strip()
    if method_filter:
        payments = payments.filter(payment_method__iexact=method_filter)
    if status_filter:
        if status_filter == 'refund_requested':
            payments = payments.filter(
                Q(payment_status='refund_requested') | 
                Q(escrow_status='refund_requested') |
                Q(booking__status='refund_requested')
            )
        else:
            payments = payments.filter(
                Q(escrow_status__iexact=status_filter) | 
                Q(payment_status__iexact=status_filter)
            )
    refund_requested_count = Payment.objects.filter(
        Q(payment_status='refund_requested') | 
        Q(escrow_status='refund_requested') |
        Q(booking__status='refund_requested')
    ).count()

    context = {
        'payments': payments,
        'method_filter': method_filter,
        'status_filter': status_filter,
        'refund_requested_count': refund_requested_count,
    }
    return render(request, 'adminpanel/payment_list.html', context)

@admin_required
def admin_payment_detail(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id)
    context = {'payment': payment}
    return render(request, 'adminpanel/payment_detail.html', context)

@admin_required
def admin_refund_payment(request, payment_id):
    if request.method == "POST":
        payment = get_object_or_404(Payment, id=payment_id)
        reason = request.POST.get('reason', 'Refund approved by administrator.')
        payment.escrow_status = 'refunded'
        payment.payment_status = 'refunded'
        if hasattr(payment, 'booking') and payment.booking:
            payment.booking.status = 'refunded'
            payment.booking.save()

        payment.save()

        # Customer Email Notification
        if payment.user:
            send_payment_status_email(payment.user, payment, 'refunded', reason)
            
        # Agent Email Notification
        if hasattr(payment, 'agent') and payment.agent:
            send_payment_status_email(payment.agent, payment, 'refunded', reason)

        messages.success(request, f"Payment #{payment.id} for Booking #{payment.booking_id} has been successfully refunded.")
        return redirect('adminpanel:payment_detail', payment_id=payment.id)
        
    return redirect('adminpanel:payment_list')

@admin_required
def admin_verify_proof(request, proof_id):
    proof = get_object_or_404(PaymentProof, pk=proof_id)

    if request.method == "POST":
        try:
            services.verify_raast_proof(proof, verified_by=request.user)

            if proof.payment and proof.payment.user:
                send_payment_status_email(proof.payment.user, proof.payment, 'proof_verified')

            messages.success(request, "Proof verified successfully! Payment is now held in escrow.")
        except (ValueError, PermissionError) as e:
            messages.error(request, f"Proof verification failed: {e}")

    return redirect('adminpanel:payment_detail', payment_id=proof.payment_id)

@admin_required
def admin_reject_proof(request, proof_id):
    proof = get_object_or_404(PaymentProof, pk=proof_id)

    if request.method == "POST":
        reason = request.POST.get('reason', 'Invalid or fake proof uploaded.')
        try:
            services.reject_raast_proof(proof, rejected_by=request.user, reason=reason)

            if proof.payment and proof.payment.user:
                send_payment_status_email(proof.payment.user, proof.payment, 'proof_rejected', reason)

            messages.warning(request, "Proof rejected. Customer will need to re-upload payment proof.")
        except (ValueError, PermissionError) as e:
            messages.error(request, f"Proof rejection failed: {e}")

    return redirect('adminpanel:payment_detail', payment_id=proof.payment_id)

@admin_required
@user_passes_test(is_admin_user, login_url='adminpanel:admin_login')
def admin_release_payment(request, payment_id):
    payment = get_object_or_404(Payment, pk=payment_id)

    if request.method == "POST":
        notes = request.POST.get('release_notes', '')
        try:
            services.release_payment(payment, released_by_admin=request.user, release_notes=notes)

            # Agent Notification
            if getattr(payment, 'agent', None):
                send_payment_status_email(payment.agent, payment, 'released', notes)

            # Customer Notification
            if getattr(payment, 'user', None):
                send_payment_status_email(payment.user, payment, 'released', notes)

            messages.success(request, f"Payment #{payment.id} released successfully.")
        except (ValueError, PermissionError, ValidationError) as e:
            messages.error(request, f"Payment release failed: {e}")

    return redirect('adminpanel:payment_detail', payment_id=payment.id)

@admin_required
@user_passes_test(is_admin_user, login_url='adminpanel:admin_login')
def admin_cancel_payment(request, payment_id):
    payment = get_object_or_404(Payment, pk=payment_id)

    if request.method == "POST":
        reason = request.POST.get('reason', '')
        try:
            services.cancel_payment(payment, cancelled_by=request.user, reason=reason)

            if payment.user:
                send_payment_status_email(payment.user, payment, 'cancelled', reason)

            messages.warning(request, f"Payment #{payment.id} has been cancelled.")
        except ValueError as e:
            messages.error(request, f"Cancellation failed: {e}")

    return redirect('adminpanel:payment_detail', payment_id=payment.id)

@admin_required
@user_passes_test(is_admin_user, login_url='adminpanel:admin_login')
def add_package_type(request):
    if request.method == "POST":
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        image = request.FILES.get('image')

        if name:
            pkg_type, created = PackageType.objects.get_or_create(
                name=name,
                defaults={
                    'description': description,
                    'image': image,
                    'is_active': True
                }
            )
            if created:
                messages.success(request, f"Package Type '{name}' added successfully.")
            else:
                messages.warning(request, f"Package Type '{name}' is already available.")
            return redirect('adminpanel:add_package_type') 
        else:
            messages.error(request, "Package Type name is mandatory.")

    package_types = PackageType.objects.all().order_by('-id')
    return render(request, 'adminpanel/package_type.html', {'package_types': package_types})


@admin_required
@user_passes_test(is_admin_user, login_url='adminpanel:admin_login')
def toggle_package_type(request, pk):
    pkg_type = get_object_or_404(PackageType, pk=pk)
    pkg_type.is_active = not pkg_type.is_active  # Toggle true/false
    pkg_type.save()
    
    status_text = "activated" if pkg_type.is_active else "deactivated"
    messages.success(request, f"Package Type '{pkg_type.name}' is now {status_text}.")
        
    return redirect('adminpanel:add_package_type')


@admin_required
@user_passes_test(is_admin_user, login_url='adminpanel:admin_login')
def delete_package_type(request, pk):
    package_type = get_object_or_404(PackageType, pk=pk)
    type_name = package_type.name
    package_type.is_active = False
    package_type.save()
    if hasattr(package_type, 'packages'):
        package_type.packages.update(is_active=False)

    messages.warning(request, f"Package Type '{type_name}' and all its connected packages have been deactivated.")
    return redirect('adminpanel:add_package_type')

@admin_required
@user_passes_test(is_admin_user, login_url='adminpanel:admin_login')
def set_commission(request):
    commission_setting, _ = CommissionSetting.objects.get_or_create(id=1)

    if request.method == "POST":
        rate = request.POST.get('commission_percentage')
        
        if not rate:
            messages.error(request, "Commission percentage field cannot be empty.")
            return redirect('adminpanel:set_commission')

        try:
            rate_val = float(rate)
            if 0 <= rate_val <= 100:
                commission_setting.commission_percentage = rate_val
                commission_setting.save()
                messages.success(request, f"Commission rate updated successfully to {rate_val}%!")
                return redirect('adminpanel:set_commission')
            else:
                messages.error(request, "Commission percentage must be between 0 and 100.")

        except (ValueError, TypeError):
            messages.error(request, "Please enter a valid numeric value.")

    total_earnings_data = PaymentRelease.objects.aggregate(
        total_admin_earnings=Sum('admin_commission_amount'),
        total_released_count=Count('id')
    )
    
    recent_releases = PaymentRelease.objects.select_related('payment', 'payment__agent').order_by('-released_at')[:10]

    context = {
        'commission_setting': commission_setting,
        'total_admin_earnings': total_earnings_data['total_admin_earnings'] or Decimal('0.00'),
        'total_released_count': total_earnings_data['total_released_count'] or 0,
        'recent_releases': recent_releases,
    }

    return render(request, 'adminpanel/set_commision.html', context)

@admin_required
@user_passes_test(is_admin_user, login_url='adminpanel:admin_login')
def admin_settings_view(request):
    settings_obj = SystemSetting.load()

    if request.method == 'POST':
        action = request.POST.get('action_type')

        if action == 'update_preferences':
            pref_form = SystemPreferenceForm(request.POST, instance=settings_obj)
            if pref_form.is_valid():
                pref_form.save()
                messages.success(request, "System preferences updated successfully!")
                return redirect('adminpanel:admin_settings')

        elif action == 'toggle_maintenance':
            settings_obj.maintenance_mode = not settings_obj.maintenance_mode
            settings_obj.save()
            status = "Enabled" if settings_obj.maintenance_mode else "Disabled"
            messages.warning(request, f"System Maintenance mode is now {status}.")
            return redirect('adminpanel:admin_settings')

        elif action == 'change_password':
            old_password = request.POST.get('old_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')

            if not request.user.check_password(old_password):
                messages.error(request, "Current password is incorrect.")
            elif new_password != confirm_password:
                messages.error(request, "New password and confirm password do not match.")
            else:
                request.user.set_password(new_password)
                request.user.save()
                update_session_auth_hash(request, request.user)
                
                send_password_change_email(request.user)

                messages.success(request, "Password changed successfully! Confirmation email sent.")
                return redirect('adminpanel:admin_settings')

    pref_form = SystemPreferenceForm(instance=settings_obj)

    context = {
        'settings': settings_obj,
        'pref_form': pref_form,
    }
    return render(request, 'adminpanel/admin_settings.html', context)

@admin_required
@user_passes_test(is_admin_user, login_url='adminpanel:admin_login')
def download_db_backup(request):
    data = serialize("json", SystemSetting.objects.all())
    response = HttpResponse(data, content_type="application/json")
    response['Content-Disposition'] = 'attachment; filename="safareharam_backup.json"'
    return response

@admin_required
@user_passes_test(is_admin_user, login_url='adminpanel:admin_login')
def guide_list(request):
    if request.user.is_staff:
        guides = GuidePage.objects.all()
    else:
        guides = GuidePage.objects.filter(is_published=True)
        
    return render(request, 'adminpanel/guide_list.html', {'guides': guides})

@admin_required
@user_passes_test(is_admin_user, login_url='adminpanel:admin_login')
def admin_guide_edit(request, page_slug):
    guide = get_object_or_404(GuidePage, page_slug=page_slug)

    if request.method == "POST":
        guide.title = request.POST.get("title")
        guide.content = request.POST.get("content")
        guide.is_published = request.POST.get("is_published") == "on"
        guide.save()

        messages.success(
            request, f"'{guide.title}' guide content updated successfully!"
        )
        return redirect("adminpanel:guide_list")

    return render(request, "adminpanel/edit_guide.html", {"guide": guide})

@admin_required
@user_passes_test(is_admin_user, login_url='adminpanel:admin_login')
def delete_guide(request, page_slug):
    if request.method == "POST":
        guide = get_object_or_404(GuidePage, page_slug=page_slug)
        guide.delete()
        messages.success(request, "Guide page deleted successfully!")
    return redirect("adminpanel:guide_list")

@require_POST
@admin_required
@user_passes_test(is_admin_user, login_url='adminpanel:admin_login')
def api_save_guide(request, page_slug):
    if not (request.user.is_authenticated and (
        request.user.is_superuser or 
        request.user.is_staff or 
        getattr(request.user, 'role', '') == 'admin'
    )):
        return JsonResponse({
            'status': 'error', 
            'message': 'Unauthorized! Only Admins or Superusers can save changes.'
        }, status=403)
    
    try:
        data = json.loads(request.body)
        content = data.get('content', '').strip()
        title = data.get('title', page_slug.capitalize() + " Guide")

        if not content:
            return JsonResponse({'status': 'error', 'message': 'Content cannot be empty.'}, status=400)
            
        guide, created = GuidePage.objects.get_or_create(
            page_slug=page_slug, 
            defaults={'title': title, 'content': content}
        )
        
        if not created:
            guide.content = content
            guide.title = title
            guide.save()

        return JsonResponse({
            'status': 'success', 
            'message': 'Page updated successfully!'
        }, status=200)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@admin_required
@user_passes_test(is_admin_user, login_url='adminpanel:admin_login')
def admin_release_payout(request, payment_id):
    if request.method == 'POST':
        payment = get_object_or_404(Payment, id=payment_id)

        if payment.payment_status == 'released' or payment.escrow_status == 'released':
            messages.info(request, f"Payment #{payment.id} payout is already released.")
            return redirect('adminpanel:payment_list')

        try:
            services.release_payment(payment, released_by_admin=request.user, release_notes="Payout released via admin dashboard.")

            if getattr(payment, 'agent', None):
                send_payment_status_email(payment.agent, payment, 'payout_released')
            if getattr(payment, 'user', None):
                send_payment_status_email(payment.user, payment, 'payout_released')

            messages.success(request, f"Payment #{payment.id} funds successfully released to Agent.")
        except Exception as e:
            messages.error(request, f"Failed to release payout: {e}")

    return redirect('adminpanel:payment_list')