from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import KYCAgentForm
from .models import AgentKYC
from django.shortcuts import render, redirect
from django.contrib import messages
# from packages.forms import PackageForm
from packages.models import Package
from packages.models import PackageType
from adminpanel.models import Complaint
from bookings.models import Bookings,BookingCustomers
from payments.models import Payment
from bookings.models import Bookings, Ticket
from payments import services
from django.db.models import Sum, F
from payments.models import Payment
from django.shortcuts import redirect, get_object_or_404
from django.core.exceptions import PermissionDenied
from base.decorators import role_required,kyc_approved_required
from bookings.models import BookingCustomers, Bookings, BookingStatusHistory
from notifications.models import Notification 
from decimal import Decimal


from django.db.models import Count, Q
 



@login_required(login_url='/auth/login/')
def agent_kyc_view(request):
    user = request.user
    profile, created = AgentKYC.objects.get_or_create(user=user)
    if created:
        profile.kyc_status = 'not_submitted'
        profile.save()
    if request.method == "GET":

        if profile.kyc_status == 'pending':
            return redirect('stakeholder:request_pending')

        if profile.kyc_status == 'rollback':
            return redirect('stakeholder:missing_doc')

        if profile.kyc_status == 'approved':
            return redirect('stakeholder:approved_agent')

        if profile.kyc_status == 'rejected':
            return redirect('stakeholder:account_locked')

    form = KYCAgentForm(request.POST or None, request.FILES or None, instance=profile)

    if request.method == "POST":

        if form.is_valid():
            obj = form.save(commit=False)

            obj.user = user
            obj.kyc_status = 'pending' 

            obj.save()

            return redirect('stakeholder:request_pending')

    return render(request, 'stakeholder/KYC.html', {
        'form': form,
        'agentkyc': profile
    })


def request_pending(request):
    agentkyc = AgentKYC.objects.filter(user=request.user).first()

    return render(request, 'stakeholder/request_pending.html', {
        'agentkyc': agentkyc
    })
@login_required(login_url='/auth/login/')

@login_required(login_url='/auth/login/')
def missing_doc(request):
    agentkyc = AgentKYC.objects.filter(user=request.user).first()

    if not agentkyc:
        return redirect('stakeholder:KYC')

    # Agar status rollback nahi hai, to is page par aane ki zaroorat nahi
    if agentkyc.kyc_status != 'rollback':
        return redirect('stakeholder:KYC')

    
    form = KYCAgentForm(
        request.POST or None,
        request.FILES or None,
        instance=agentkyc
    )

    if request.method == "POST":
        if form.is_valid():
            obj = form.save(commit=False)
            obj.kyc_status = "pending"  
            
           
            obj.submission_count += 1
            obj.save()

            messages.success(
                request,
                "Documents re-submitted successfully. Waiting for admin approval."
            )
            return redirect('stakeholder:request_pending')

    return render(
        request,
        'stakeholder/missing_doc.html',
        {
            'form': form,
            'agentkyc': agentkyc,
        }
    )
@login_required(login_url='/auth/login/')
def approved_agent(request):
    
    agentkyc = AgentKYC.objects.filter(user=request.user).first()

    return render(request, 'stakeholder/approved_agent.html', {
        'agentkyc': agentkyc,
        'admin_comment': agentkyc.admin_comment if agentkyc else ""
    })
@login_required(login_url='/accounts/login/')
def agent_details(request):
    agentkyc = AgentKYC.objects.filter(user=request.user).first()

    return render(request, 'stakeholder/view_profile.html', {
        'agentkyc': agentkyc
    })
@login_required(login_url='/accounts/login/')
def account_locked(request):
    agentkyc = AgentKYC.objects.filter(user=request.user).first()

    return render(request, 'stakeholder/account_locked.html', {
        'agentkyc': agentkyc
    })

@role_required('stakeholder')
@kyc_approved_required
@login_required(login_url='/auth/login/')
def stakeholder_dashboard(request):
    user = request.user

    # 1. Packages Stats
    user_packages = Package.objects.filter(agency=user)
    total_packages_count = user_packages.count()
    
    # Draft, Pending, ya Inactive packages count karein
    pending_packages_count = user_packages.filter(
        Q(status='draft') | Q(status='pending') | Q(status='inactive')
    ).count()

    # 2. Bookings Stats
    agent_bookings = Bookings.objects.filter(package__agency=user)

    # In tamam active statuses ko consider karein jo valid booking hain
    active_statuses = [
        'confirmed', 
        'processing', 
        'visa_processing', 
        'ticket_issued', 
        'completed'
    ]
    
    active_bookings = agent_bookings.filter(status__in=active_statuses)
    active_bookings_count = active_bookings.count()

    # 3. Total Earnings (Total Amount Sum)
    # Target values: total_amount ya paid_amount
    total_earnings_query = active_bookings.aggregate(total=Sum('total_amount'))
    total_earnings = total_earnings_query['total'] if total_earnings_query['total'] else 0

    # 4. Recent Bookings (Top 5)
    recent_bookings = agent_bookings.select_related('package', 'user').order_by('-created_at')[:5]

    # 5. Notifications system
    notifications = Notification.objects.filter(
        recipient=user,
        is_deleted=False
    ).order_by('-created_at')[:5]

    unread_notifications_count = Notification.objects.filter(
        recipient=user,
        is_read=False,
        is_deleted=False
    ).count()

    context = {
        'total_packages_count': total_packages_count,
        'pending_packages_count': pending_packages_count,
        'active_bookings_count': active_bookings_count,
        'total_earnings': total_earnings,
        'recent_bookings': recent_bookings,
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
    }

    return render(request, 'stakeholder/stakeholder_dashboard.html', context)




def agent_complaints(request):
    COMPLAINT_TYPES = [
        ('booking_issue', 'Booking & Ticket Issue'),
        ('payment_escrow', 'Escrow & Payout Issue'),
        ('hotel_partner', 'Hotel Partner Discrepancy'),
        ('package_listing', 'Package Listing Query'),
        ('tech_support', 'Technical / System Error'),
        ('other', 'Other Grievance'),
    ]

    if request.method == "POST":
        complaint_type = request.POST.get("complaint_type")
        subject = request.POST.get("subject")
        description = request.POST.get("description")
        
        Complaint.objects.create(
            user=request.user, 
            complaint_type=complaint_type,
            subject=subject,
            description=description,
            status='pending'
        )
        messages.success(request, "Agency complaint submitted successfully. Support team will contact you shortly.")
        return redirect(request.path)
    agency_complaints = Complaint.objects.filter(user=request.user).order_by('-created_at')
    counts = agency_complaints.aggregate(
        total=Count('id'),
        pending=Count('id', filter=Q(status='pending')),
        in_progress=Count('id', filter=Q(status='in_progress')),
        resolved=Count('id', filter=Q(status='resolved'))
    )

    context = {
        'issues': COMPLAINT_TYPES,
        'agency_complaints': agency_complaints,
        'counts': counts,
    }
    return render(request, 'stakeholder/agent_complaints.html', context)

def cancelled_booking(request):
    return render(request, 'stakeholder/cancelled_booking.html')

def view_profile(request):
    agentkyc = AgentKYC.objects.filter(user=request.user).first()
    if request.method == 'POST':
        if not agentkyc:
            messages.error(request, "Please complete your KYC first.")
            return redirect('stakeholder:view_profile')

        agentkyc.phone_no = request.POST.get('phone_no', agentkyc.phone_no)
        agentkyc.whatsapp_no = request.POST.get('whatsapp_no', agentkyc.whatsapp_no)
        agentkyc.raast_id = request.POST.get('raast_id', agentkyc.raast_id)
        agentkyc.save()
        messages.success(request, "Your profile has been updated successfully.")
        return redirect('stakeholder:view_profile')
    context = {
        'agentkyc': agentkyc,
    }
    return render(request, 'stakeholder/view_profile.html', context)

@login_required(login_url='/auth/login/')
def payments(request):
    payments = Payment.objects.filter(
        agent=request.user,
        escrow_status__in=['held_in_escrow', 'released']  
    ).select_related('booking', 'customer').order_by('-created_at')

    context = {'payments': payments}
    return render(request, 'stakeholder/payments.html', context)


@login_required(login_url='/auth/login/')
def agent_upload_ticket(request, booking_id):
    booking = get_object_or_404(Bookings, pk=booking_id, package__agency=request.user)
    payment = getattr(booking, 'payment', None)

    if not payment or payment.escrow_status != 'held_in_escrow':
        messages.error(request, "ticket upload only when payment is in escrow")
        return redirect('stakeholder:payments')

    if hasattr(booking, 'ticket'):
        messages.info(request, "ticket already uploaded")
        return redirect('stakeholder:payments')

    if request.method == "POST":
        ticket_file = request.FILES.get('ticket_file')
        notes = request.POST.get('notes', '')

        if not ticket_file:
            messages.error(request, "Ticket file select karein.")
            return redirect('stakeholder:ticket_send', booking_id=booking.id)

        Ticket.objects.create(
            booking=booking,
            agent=request.user,
            ticket_file=ticket_file,
            notes=notes,
        )

        try:
            services.mark_ticket_uploaded(payment)
            messages.success(request, "ticket upload wait for the customer approval.")
        except ValueError as e:
            messages.error(request, f"Status is not updated: {e}")

        return redirect('stakeholder:payments')

    return render(request, 'stakeholder/ticket_send.html', {'booking': booking, 'payment': payment})
@login_required(login_url='/auth/login/')
def escrow_status_overview(request):
    payments = Payment.objects.filter(
        customer=request.user
    ).select_related('booking', 'booking__package').order_by('-created_at')
    context = {'payments': payments}
    return render(request, 'customer/escrow_status.html', context)





@login_required(login_url='/auth/login/')
def earning_transaction(request):
    # Select related release_record so we can fetch calculated release numbers directly
    agent_payments = Payment.objects.filter(
        booking__package__agency=request.user
    ).select_related('booking', 'booking__user', 'booking__package', 'release_record').order_by('-created_at')
    
    # Case-insensitive status filter for released payments
    released_payments = agent_payments.filter(escrow_status__iexact='released')
    
    # Total Gross Amount
    total_earnings = released_payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    # Dynamic Net Earning & Commission Calculation
    net_payable = Decimal('0.00')
    commission_deducted = Decimal('0.00')

    for payment in released_payments:
        if hasattr(payment, 'release_record') and payment.release_record:
            # PaymentRelease table se exact system-calculated commission fetch karein
            net_payable += payment.release_record.amount_released
            commission_deducted += payment.release_record.admin_commission_amount
        else:
            # Fallback calculation (Agar PaymentRelease entry fail ho jaye)
            comm_rate = Decimal('10.00') # 10%
            comm = (payment.amount * comm_rate) / Decimal('100.00')
            commission_deducted += comm
            net_payable += (payment.amount - comm)

    context = {
        'payments': agent_payments,
        'total_earnings': total_earnings,
        'commission_deducted': commission_deducted,
        'net_payable': net_payable,
    }
    
    return render(request, 'stakeholder/earning_transaction.html', context)


@login_required
def booking_detail(request, booking_id):
    booking = get_object_or_404(Bookings, pk=booking_id)
    customers = BookingCustomers.objects.filter(booking=booking)
    
    return render(request, 'stakeholder/booking_detail.html', {
        'booking': booking,
        'customers': customers
    })



@login_required(login_url='/auth/login/')
def manage_booking(request):
    bookings_list = Bookings.objects.filter(
        package__agency=request.user
    ).select_related('package', 'user', 'payment').order_by('-created_at')
    
    status_filter = request.GET.get('status')
    if status_filter:
        bookings_list = bookings_list.filter(status=status_filter)
        
    search_query = request.GET.get('search')
    if search_query:
        bookings_list = bookings_list.filter(
            id__icontains=search_query
        ) | bookings_list.filter(
            user__username__icontains=search_query
        )
        
    all_bookings = Bookings.objects.filter(package__agency=request.user)
    stats = {
        'total': all_bookings.count(),
        'pending': all_bookings.filter(status='pending').count(),
        'action_required': all_bookings.filter(status='action_required').count(),
        'visa_processing': all_bookings.filter(status='visa_processing').count(),
        'ticket_issued': all_bookings.filter(status='ticket_issued').count(),
        'completed': all_bookings.filter(status='completed').count(),
        'cancelled': all_bookings.filter(status='cancelled').count(),
    }

    context = {
        'bookings': bookings_list,
        'stats': stats,
        'current_status': status_filter or '',
        'search_query': search_query or '',
    }
    return render(request, 'stakeholder/manage_booking.html', context)


@login_required
def verify_booking_doc(request, customer_id):
    customer = get_object_or_404(BookingCustomers, id=customer_id)
    booking = customer.booking

    if request.method == 'POST':
        review_fields = [
            'full_name', 'phone_number', 'email', 'cnic', 
            'passport_number', 'passport_expiry',
            'passport_scan', 'passport_photo', 'cnic_front', 'cnic_back'
        ]

        field_statuses = {}
        rollback_remarks = {}
        has_rejection = False

        for field in review_fields:
            status_val = request.POST.get(f'field_status_{field}', 'approved')
            remark_val = request.POST.get(f'remark_{field}', '').strip()

            field_statuses[field] = status_val
            if status_val == 'rejected':
                has_rejection = True
                if remark_val:
                    rollback_remarks[field] = remark_val

        customer.field_statuses = field_statuses
        customer.rollback_remarks = rollback_remarks
        old_status = booking.status

        if has_rejection:
            customer.verification_status = 'rollback'
            booking.status = 'action_required'
            booking.save()
            notif_msg = f"Action required on documents for {customer.full_name} (Booking #{booking.id}). Please update rejected fields."
            BookingStatusHistory.objects.create(
                booking=booking,
                old_status=old_status,
                new_status='action_required',
                changed_by=request.user,
                comments=f"Documents rejected for {customer.full_name}. Corrections requested."
            )
        else:
            customer.verification_status = 'approved'
            all_customers = BookingCustomers.objects.filter(booking=booking)
            
            if all_customers.filter(verification_status='approved').count() == all_customers.count():
                booking.status = 'docs_verified'
                booking.save()
                BookingStatusHistory.objects.create(
                    booking=booking,
                    old_status=old_status,
                    new_status='docs_verified',
                    changed_by=request.user,
                    comments="All customer documents successfully verified."
                )
            
            notif_msg = f"Documents for {customer.full_name} have been approved."

        customer.save()
        Notification.objects.create(
            recipient=booking.user,
            title="Document Verification Update",
            message=notif_msg
        )

        messages.success(request, f"Verification decisions saved for {customer.full_name}.")
        return redirect('stakeholder:booking_detail', booking_id=booking.id)


@login_required(login_url="/auth/login/")
def update_booking_status(request, booking_id):
    booking = get_object_or_404(Bookings, pk=booking_id, package__agency=request.user)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "visa_processing":
            old_status = booking.status
            booking.status = "visa_processing"
            booking.save()

            BookingStatusHistory.objects.create(
                booking=booking,
                old_status=old_status,
                new_status="visa_processing",
                changed_by=request.user,
                comments="Visa processing initiated by agent.",
            )
            Notification.objects.create(
                recipient=booking.user,
                title="Visa Processing Started",
                message=f"Your visa processing for Booking #{booking.id} has been initiated."
            )
            messages.info(request, "Visa processing status is active.")

        elif action == "upload_ticket":
            ticket_file = request.FILES.get("ticket_file")
            notes = request.POST.get("notes", "")

            if ticket_file:
                Ticket.objects.update_or_create(
                    booking=booking,
                    defaults={
                        "agent": request.user,
                        "ticket_file": ticket_file,
                        "notes": notes,
                    },
                )

                old_status = booking.status
                booking.status = "ticket_issued"
                booking.save()

                BookingStatusHistory.objects.create(
                    booking=booking,
                    old_status=old_status,
                    new_status="ticket_issued",
                    changed_by=request.user,
                    comments="e-Ticket uploaded by agent.",
                )

                # Customer Notification
                Notification.objects.create(
                    recipient=booking.user,
                    title="Ticket Issued",
                    message=f"Ticket uploaded for Booking #{booking.id}. Please review and approve in your dashboard."
                )
                messages.success(request, "Ticket uploaded")

    return redirect("stakeholder:booking_detail", booking_id=booking.pk)