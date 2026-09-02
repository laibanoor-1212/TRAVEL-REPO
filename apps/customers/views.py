from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import CustomerProfile
from adminpanel.models import Complaint
from payments.models import Payment
from bookings.models import Bookings, Ticket 
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.utils import timezone
from payments import services
from django.core.exceptions import PermissionDenied
from base.decorators import role_required
from django.db.models import Sum, Count, Q
from payments.models import Payment
from bookings.models import BookingCustomers, BookingStatusHistory

from adminpanel.decorators import user_required

# --- EMAIL IMPORTS (ADDED FOR UTILS INTEGRATION) ---
from utils.emails import (
    send_complaint_submitted_emails,
    send_ticket_approved_notification,
    send_ticket_rejected_notification,
    send_booking_action_email,
    send_docs_resubmitted_email,
)


@login_required(login_url='/auth/login/')
def user_profile_view(request):
    profile, created = CustomerProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Personal Fields
        profile.full_name = request.POST.get('full_name')
        profile.father_name = request.POST.get('father_name')
        profile.gender = request.POST.get('gender')
        profile.marital_status = request.POST.get('marital_status')
        profile.phone = request.POST.get('phone')
        
        dob = request.POST.get('date_of_birth')
        profile.date_of_birth = dob if dob else None
        
        profile.country = request.POST.get('country', 'Pakistan')
        profile.province = request.POST.get('province')
        profile.city = request.POST.get('city')
        profile.address = request.POST.get('address')
        profile.cnic_number = request.POST.get('cnic_number')
        
        # Preferences & Emergency Contact
        profile.emergency_contact_name = request.POST.get('emergency_contact_name')
        profile.relation = request.POST.get('relation')
        profile.emergency_contact_phone = request.POST.get('emergency_contact_phone')
        profile.medical_condition = request.POST.get('medical_condition')
        profile.wheelchair_required = 'wheelchair_required' in request.POST
        profile.budget_preference = request.POST.get('budget_preference')
        profile.travel_type = request.POST.get('travel_type')
        packages_list = request.POST.getlist('interested_packages')
        profile.interested_packages = ",".join(packages_list) if packages_list else ""
        
        # Files handling
        if 'cnic_front' in request.FILES:
            profile.cnic_front = request.FILES['cnic_front']
        if 'cnic_back' in request.FILES:
            profile.cnic_back = request.FILES['cnic_back']

        profile.is_profile_completed = True
        profile.save()
        return redirect('customers:user_profile_view')
        
    saved_packages = profile.interested_packages.split(',') if profile.interested_packages else []

    context = {
        'profile': profile,
        'saved_packages': saved_packages
    }
    return render(request, 'customer/user_profile.html', context)


@user_required
@login_required(login_url='/auth/login/')
def customer_kyc(request):
   
    try:
        profile = CustomerProfile.objects.get(user=request.user)
    except CustomerProfile.DoesNotExist:
        profile = CustomerProfile(user=request.user) 

    if request.method == 'POST':
        profile.full_name = request.POST.get('full_name')
        profile.father_name = request.POST.get('father_name')
        profile.gender = request.POST.get('gender')
        profile.marital_status = request.POST.get('marital_status')
        profile.phone = request.POST.get('phone')
        
        dob = request.POST.get('date_of_birth')
        profile.date_of_birth = dob if dob else None
        
        profile.country = request.POST.get('country', 'Pakistan')
        profile.province = request.POST.get('province')
        profile.city = request.POST.get('city')
        profile.address = request.POST.get('address')
        profile.cnic_number = request.POST.get('cnic_number') or None  
        
        profile.emergency_contact_name = request.POST.get('emergency_contact_name')
        profile.relation = request.POST.get('relation')
        profile.emergency_contact_phone = request.POST.get('emergency_contact_phone')
        profile.medical_condition = request.POST.get('medical_condition')
        profile.wheelchair_required = 'wheelchair_required' in request.POST
        profile.budget_preference = request.POST.get('budget_preference')
        profile.travel_type = request.POST.get('travel_type')
        
        packages_list = request.POST.getlist('interested_packages')
        profile.interested_packages = ",".join(packages_list) if packages_list else ""
        
        if 'cnic_front' in request.FILES:
            profile.cnic_front = request.FILES['cnic_front']
        if 'cnic_back' in request.FILES:
            profile.cnic_back = request.FILES['cnic_back']

        profile.is_profile_completed = True
        profile.save() 
        return redirect('customers:user_dashboard') 
    return render(request, 'customer/customer_kyc.html', {'profile': profile})


@user_required
@login_required(login_url='/auth/login/')
def user_bookings(request):
    current_user_bookings = Bookings.objects.filter(user=request.user).order_by('-created_at')
    context = {
        'bookings': current_user_bookings
    }
    return render(request, 'customer/user_booking.html', context)


@user_required
@role_required('user')
@login_required(login_url='/auth/login/')
def user_dashboard(request):
    return render(request, 'customer/user_layout.html')


@user_required
@login_required(login_url='/auth/login/')
def overview_user(request):
    user = request.user

    # Active Booking
    active_booking = Bookings.objects.filter(
        user=user
    ).exclude(
        status__in=['completed', 'cancelled']
    ).select_related('package', 'package__agency').order_by('-created_at').first()

    # Counters
    user_bookings = Bookings.objects.filter(user=user)
    total_bookings_count = user_bookings.count()
    active_bookings_count = user_bookings.exclude(status__in=['completed', 'cancelled']).count()
    completed_bookings_count = user_bookings.filter(status='completed').count()
    tickets_count = user_bookings.filter(status__in=['confirmed', 'completed']).count()

    # Payment Calculations
    user_payments = Payment.objects.filter(customer=user)

    # 1. Total Paid Amount
    total_amount_paid = user_payments.aggregate(
        total=Sum('amount')
    )['total'] or 0.00

    # 2. Escrow Hold Amount (Check status case-insensitively)
    escrow_hold_amount = user_payments.filter(
        Q(escrow_status__iexact='hold') | Q(escrow_status__iexact='in_escrow') | Q(escrow_status__iexact='escrow')
    ).aggregate(
        total=Sum('amount')
    )['total'] or 0.00

    # 3. Escrow Released Amount
    escrow_released_amount = user_payments.filter(
        Q(escrow_status__iexact='released') | Q(escrow_status__iexact='completed')
    ).aggregate(
        total=Sum('amount')
    )['total'] or 0.00

    context = {
        'active_booking': active_booking,
        'total_bookings_count': total_bookings_count,
        'active_bookings_count': active_bookings_count,
        'completed_bookings_count': completed_bookings_count,
        'tickets_count': tickets_count,
        'total_amount_paid': total_amount_paid,
        'escrow_hold_amount': escrow_hold_amount,
        'escrow_released_amount': escrow_released_amount,
    }

    return render(request, 'customer/overview_user.html', context)


@user_required
def customer_complaints(request):
    COMPLAINT_TYPES = [
        ('ticket', 'Ticket & Booking Issue'),
        ('hotel', 'Hotel & Accommodation Issue'),
        ('transport', 'Transport & Transfers'),
        ('payment', 'Payment & Refund Query'),
        ('visa', 'Visa Processing Issue'),
        ('other', 'Other General Inquiry'),
    ]

    if request.method == "POST":
        complaint_type = request.POST.get("complaint_type")
        subject = request.POST.get("subject")
        description = request.POST.get("description")
        
        complaint = Complaint.objects.create(
            user=request.user,
            complaint_type=complaint_type,
            subject=subject,
            description=description,
            status='pending'
        )

        # Trigger Emails (Customer + Admin)
        try:
            send_complaint_submitted_emails(
                user_email=request.user.email,
                user_name=request.user.get_full_name() or request.user.username,
                complaint_id=complaint.id,
                complaint_type=complaint_type,
                subject_text=subject,
                description=description or ""
            )
        except Exception:
            pass

        messages.success(request, "Aapki complaint successfully submit ho gayi hai!")
        return redirect(request.path)

    # Current logged-in user ki tamaam complaints
    my_complaints = Complaint.objects.filter(user=request.user).order_by('-created_at')
    
    # Status Counts Dynamic Calculation
    counts = my_complaints.aggregate(
        total=Count('id'),
        pending=Count('id', filter=Q(status='pending')),
        in_progress=Count('id', filter=Q(status='in_progress')),
        resolved=Count('id', filter=Q(status='resolved'))
    )

    context = {
        'issues': COMPLAINT_TYPES,
        'my_complaints': my_complaints,
        'counts': counts,
    }
    return render(request, 'customer/customer_complaints.html', context)


@user_required
@login_required(login_url='/auth/login/')
def escrow_status_overview(request):
    payments = Payment.objects.filter(
        customer=request.user
    ).select_related('booking', 'booking__package').order_by('-created_at')

    context = {'payments': payments}
    return render(request, 'customer/customer_escrow_status.html', context)


@user_required
@login_required(login_url='/auth/login/')
def user_ticket(request):
    bookings = (
        Bookings.objects.filter(user=request.user, ticket__isnull=False)
        .select_related('package', 'ticket')
        .order_by('-id')
    )
    return render(request, 'customer/user_ticket.html', {'bookings': bookings})


@user_required
def approve_ticket(request, booking_id):
    if request.method == "POST":
        booking = get_object_or_404(Bookings, id=booking_id, user=request.user)
        
        try:
            ticket = booking.ticket 
            ticket.customer_approved = True
            ticket.customer_approved_at = timezone.now()
            ticket.customer_rejection_reason = None 
            ticket.save()

            # Trigger Email to Agent/Admin
            try:
                agent_email = getattr(getattr(getattr(booking, 'package', None), 'agent', None), 'email', None)
                send_ticket_approved_notification(
                    agent_email=agent_email,
                    customer_name=request.user.get_full_name() or request.user.username,
                    booking_id=booking.id
                )
            except Exception:
                pass

            messages.success(request, "Ticket successfully approved!")
        except Ticket.DoesNotExist:
            messages.error(request, "Ticket is not uploaded for this booking.")
            
        return redirect('customers:user_ticket')  


@user_required
def reject_ticket_view(request, booking_id):
    if request.method == "POST":
        booking = get_object_or_404(Bookings, id=booking_id, user=request.user)
        reason = request.POST.get('reason')
        
        try:
            ticket = booking.ticket
            ticket.customer_approved = False
            ticket.customer_rejection_reason = reason
            ticket.save()

            # Trigger Email to Agent/Admin
            try:
                agent_email = getattr(getattr(getattr(booking, 'package', None), 'agent', None), 'email', None)
                send_ticket_rejected_notification(
                    agent_email=agent_email,
                    customer_name=request.user.get_full_name() or request.user.username,
                    booking_id=booking.id,
                    reason=reason or ""
                )
            except Exception:
                pass

            messages.success(request, "Ticket rejection status updated.")
        except Ticket.DoesNotExist:
            messages.error(request, "Ticket record nahi mila.")
            
        return redirect('customers:user_ticket')


@user_required
@login_required
def manage_booking_request(request, booking_id):
    booking = get_object_or_404(Bookings, id=booking_id)
    is_customer = booking.user == request.user
    is_admin = request.user.is_staff or getattr(request.user, 'role', '') == 'admin'

    if not (is_customer or is_admin):
        messages.error(request, "Aap ke paas is booking ko manage karne ki permission nahi hai.")
        return redirect('customers:user_bookings')

    if request.method == "POST":
        action_type = request.POST.get("action_type")
        reason = request.POST.get("reason")
        agent_email = getattr(getattr(getattr(booking, 'package', None), 'agent', None), 'email', None)

        if action_type == "cancel":
            old_status = booking.status
            booking.status = "cancelled"
            
            if reason:
                booking.customer_note = reason
                
            booking.save()

            BookingStatusHistory.objects.create(
                booking=booking,
                old_status=old_status,
                new_status="cancelled",
                changed_by=request.user,
                remarks=reason or "Cancellation requested by customer"
            )

            # Email Notification
            try:
                send_booking_action_email(
                    action_type="cancel",
                    customer_email=request.user.email,
                    customer_name=request.user.get_full_name() or request.user.username,
                    booking_id=booking.id,
                    agent_email=agent_email,
                    reason=reason or ""
                )
            except Exception:
                pass

            messages.success(request, "Aap ki booking cancellation request successfully submit ho gayi hai.")
            return redirect('customers:user_bookings')

        elif action_type == "refund":
            if hasattr(booking, 'payment') and booking.payment:
                payment = booking.payment
                
                if payment.payment_status in ['held_in_escrow', 'paid']:
                    payment.payment_status = 'refund_requested' 
                    payment.refund_reason = reason
                    payment.save()

                    booking.status = 'refund_requested'
                    booking.customer_note = reason
                    booking.save()

                    BookingStatusHistory.objects.create(
                        booking=booking,
                        old_status=booking.status,
                        new_status="refund_requested",
                        changed_by=request.user,
                        remarks=reason or "Refund requested by customer"
                    )

                    # Email Notification
                    try:
                        send_booking_action_email(
                            action_type="refund",
                            customer_email=request.user.email,
                            customer_name=request.user.get_full_name() or request.user.username,
                            booking_id=booking.id,
                            agent_email=agent_email,
                            reason=reason or ""
                        )
                    except Exception:
                        pass

                    messages.success(request, "Refund request successfully submited. Admin review it.")
                else:
                    messages.error(request, "In this payment status refund request is not able to submit.")
            else:
                messages.error(request, "this booking do not have valid payment record.")

            return redirect('customers:user_bookings')

        elif action_type == "extend":
            new_date = request.POST.get("new_date")
            booking.requested_extension_date = new_date  
            booking.customer_note = reason
            booking.save()

            # Email Notification
            try:
                send_booking_action_email(
                    action_type="extend",
                    customer_email=request.user.email,
                    customer_name=request.user.get_full_name() or request.user.username,
                    booking_id=booking.id,
                    agent_email=agent_email,
                    reason=reason or "",
                    new_date=new_date or ""
                )
            except Exception:
                pass

            messages.success(request, "Date extension request submited.")
            return redirect('customers:user_bookings')

    return redirect('customers:user_bookings')


@user_required
@login_required(login_url='/auth/login/')
def booking_detail(request, booking_id):
    booking = get_object_or_404(Bookings, pk=booking_id, user=request.user)
    customers = BookingCustomers.objects.filter(booking=booking)
    
    return render(request, 'customer/booking_detail.html', {
        'booking': booking,
        'customers': customers
    })


@user_required
@login_required(login_url='/auth/login/')
def update_booking_docs(request, booking_id):
    booking = get_object_or_404(Bookings, id=booking_id, user=request.user)
    customers = BookingCustomers.objects.filter(booking=booking)

    if request.method == 'POST':
        for customer in customers:
            field_statuses = customer.field_statuses or {}

            if field_statuses.get('full_name') == 'rejected':
                customer.full_name = request.POST.get(f'full_name_{customer.id}', customer.full_name)
                field_statuses['full_name'] = 'pending'

            if field_statuses.get('phone_number') == 'rejected':
                customer.phone_number = request.POST.get(f'phone_number_{customer.id}', customer.phone_number)
                field_statuses['phone_number'] = 'pending'

            if field_statuses.get('email') == 'rejected':
                customer.email = request.POST.get(f'email_{customer.id}', customer.email)
                field_statuses['email'] = 'pending'

            if field_statuses.get('cnic') == 'rejected':
                customer.cnic = request.POST.get(f'cnic_{customer.id}', customer.cnic)
                field_statuses['cnic'] = 'pending'

            if field_statuses.get('passport_number') == 'rejected':
                customer.passport_number = request.POST.get(f'passport_number_{customer.id}', customer.passport_number)
                field_statuses['passport_number'] = 'pending'

            if field_statuses.get('passport_expiry') == 'rejected':
                expiry_val = request.POST.get(f'passport_expiry_{customer.id}')
                if expiry_val:
                    customer.passport_expiry = expiry_val
                    field_statuses['passport_expiry'] = 'pending'
            if field_statuses.get('passport_scan') == 'rejected' and f'passport_scan_{customer.id}' in request.FILES:
                customer.passport_scan = request.FILES[f'passport_scan_{customer.id}']
                field_statuses['passport_scan'] = 'pending'

            if field_statuses.get('passport_photo') == 'rejected' and f'passport_photo_{customer.id}' in request.FILES:
                customer.passport_photo = request.FILES[f'passport_photo_{customer.id}']
                field_statuses['passport_photo'] = 'pending'

            if field_statuses.get('cnic_front') == 'rejected' and f'cnic_front_{customer.id}' in request.FILES:
                customer.cnic_front = request.FILES[f'cnic_front_{customer.id}']
                field_statuses['cnic_front'] = 'pending'

            if field_statuses.get('cnic_back') == 'rejected' and f'cnic_back_{customer.id}' in request.FILES:
                customer.cnic_back = request.FILES[f'cnic_back_{customer.id}']
                field_statuses['cnic_back'] = 'pending'
            customer.field_statuses = field_statuses
            customer.verification_status = 'resubmitted'
            customer.save()
        old_status = booking.status
        booking.status = 'under_review'
        booking.save()
        BookingStatusHistory.objects.create(
            booking=booking,
            old_status=old_status,
            new_status='under_review',
            changed_by=request.user,
            comments="Customer re-submitted rejected documents/details for verification."
        )

        # Trigger Re-submitted Email
        try:
            agent_email = getattr(getattr(getattr(booking, 'package', None), 'agent', None), 'email', None)
            send_docs_resubmitted_email(
                customer_name=request.user.get_full_name() or request.user.username,
                booking_id=booking.id,
                agent_email=agent_email
            )
        except Exception:
            pass

        messages.success(request, "Corrections & updated documents re-submitted successfully!")
        return redirect('customers:booking_detail', booking_id=booking.id)

    return render(request, 'customer/update_docs.html', {
        'booking': booking,
        'customers': customers
    })