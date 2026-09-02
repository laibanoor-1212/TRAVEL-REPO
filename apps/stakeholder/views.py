from decimal import Decimal
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Count, F, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from adminpanel.models import Complaint
from base.decorators import kyc_approved_required, role_required
from bookings.models import BookingCustomers, Bookings, BookingStatusHistory, Ticket
from notifications.models import Notification
from packages.models import Package, PackageType
from payments import services
from payments.models import Payment
from .forms import KYCAgentForm
from .models import AgentKYC

# Email Utility Helpers Import
from utils.emails import (
    send_admin_new_agent_alert,
    send_complaint_submitted_emails,
    send_docs_resubmitted_email,
    send_booking_status_email,
    send_document_status_update_email,
    send_ticket_uploaded_notification,
)


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

            # Trigger email notification to Admin for new KYC request
            send_admin_new_agent_alert(
                agent_name=user.get_full_name() or user.username,
                agent_email=user.email,
                agency_name=getattr(profile, 'agency_name', '')
            )

            return redirect('stakeholder:request_pending')

    return render(request, 'stakeholder/KYC.html', {
        'form': form,
        'agentkyc': profile
    })


@login_required(login_url='/auth/login/')
def request_pending(request):
    agentkyc = AgentKYC.objects.filter(user=request.user).first()
    return render(request, 'stakeholder/request_pending.html', {
        'agentkyc': agentkyc
    })


@login_required(login_url='/auth/login/')
def missing_doc(request):
    agentkyc = AgentKYC.objects.filter(user=request.user).first()

    if not agentkyc or agentkyc.kyc_status != 'rollback':
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

            # Trigger email notification for re-submitted documents
            send_admin_new_agent_alert(
                agent_name=request.user.get_full_name() or request.user.username,
                agent_email=request.user.email,
                agency_name="Resubmitted KYC Documents"
            )

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

    user_packages = Package.objects.filter(agency=user)
    total_packages_count = user_packages.count()
    
    pending_packages_count = user_packages.filter(
        Q(status='draft') | Q(status='pending') | Q(status='inactive')
    ).count()

    agent_bookings = Bookings.objects.filter(package__agency=user)

    active_statuses = [
        'confirmed', 
        'processing', 
        'visa_processing', 
        'ticket_issued', 
        'completed'
    ]
    
    active_bookings = agent_bookings.filter(status__in=active_statuses)
    active_bookings_count = active_bookings.count()

    total_earnings_query = active_bookings.aggregate(total=Sum('total_amount'))
    total_earnings = total_earnings_query['total'] if total_earnings_query['total'] else 0

    recent_bookings = agent_bookings.select_related('package', 'user').order_by('-created_at')[:5]

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


@login_required(login_url='/auth/login/')
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
        
        complaint = Complaint.objects.create(
            user=request.user, 
            complaint_type=complaint_type,
            subject=subject,
            description=description,
            status='pending'
        )

        # Send complaint confirmation to User and alert to Admin
        send_complaint_submitted_emails(
            user_email=request.user.email,
            user_name=request.user.get_full_name() or request.user.username,
            complaint_id=complaint.id,
            complaint_type=complaint_type,
            subject_text=subject,
            description=description
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


@login_required(login_url='/auth/login/')
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


@login_required
def payments(request):
    if not (getattr(request.user, 'role', '') == 'stakeholder' or request.user.is_staff):
        messages.error(request, "You do not have access to this page.")
        return redirect('customers:user_dashboard')

    payments_list = Payment.objects.filter(agent=request.user).select_related(
        'customer', 
        'booking', 
        'booking__ticket'
    ).order_by('-created_at')

    context = {
        'payments': payments_list,
    }
    return render(request, 'stakeholder/payments.html', context)


@login_required
def agent_request_payout(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id)

    package = getattr(payment.booking, 'package', None)
    if package:
        package_owner = getattr(package, 'created_by', None) or \
                        getattr(package, 'user', None) or \
                        getattr(package, 'agent', None) or \
                        getattr(package, 'stakeholder', None) or \
                        getattr(package, 'agency', None)
        
        if package_owner and package_owner != request.user:
            messages.error(request, "You are not authorized to request payout for this payment.")
            return redirect('stakeholder:payments')

    if not hasattr(payment.booking, 'ticket'):
        messages.error(request, "Please upload the ticket before requesting payout.")
        return redirect('stakeholder:payments')

    if request.method == 'POST':
        if hasattr(payment, 'payout_status'):
            payment.payout_status = 'requested'
        elif hasattr(payment, 'is_payout_requested'):
            payment.is_payout_requested = True
        
        payment.save()

        if request.user.email:
            send_mail(
                subject=f"Safar-e-Haram: Payout Requested for Booking #{payment.booking.id}",
                message=f"Hello {request.user.username},\n\nYour payout request for Booking #{payment.booking.id} (Amount: PKR {payment.amount}) has been submitted and is currently being processed.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[request.user.email],
                fail_silently=True,
            )

        messages.success(request, "Payout request submitted successfully!")
        return redirect('stakeholder:payments')

    return redirect('stakeholder:payments')


@login_required(login_url='/auth/login/')
def agent_upload_ticket(request, booking_id):
    booking = get_object_or_404(Bookings, pk=booking_id, package__agency=request.user)
    payment = getattr(booking, 'payment', None)

    if not payment or payment.escrow_status != 'held_in_escrow':
        messages.error(request, "Ticket upload is only allowed when payment is in escrow.")
        return redirect('stakeholder:payments')

    if hasattr(booking, 'ticket'):
        messages.info(request, "Ticket already uploaded.")
        return redirect('stakeholder:payments')

    if request.method == "POST":
        ticket_file = request.FILES.get('ticket_file')
        notes = request.POST.get('notes', '')

        if not ticket_file:
            messages.error(request, "Please select a ticket file.")
            return redirect('stakeholder:ticket_send', booking_id=booking.id)

        Ticket.objects.create(
            booking=booking,
            agent=request.user,
            ticket_file=ticket_file,
            notes=notes,
        )

        try:
            services.mark_ticket_uploaded(payment)

            send_ticket_uploaded_notification(
                customer_email=booking.user.email,
                customer_name=booking.user.get_full_name() or booking.user.username,
                booking_id=booking.id,
                agent_name=request.user.get_full_name() or request.user.username
            )

            messages.success(request, "Ticket uploaded. Waiting for customer approval.")
        except ValueError as e:
            messages.error(request, f"Status is not updated: {e}")

        return redirect('stakeholder:payments')

    return render(request, 'stakeholder/ticket_send.html', {'booking': booking, 'payment': payment})


@login_required(login_url='/auth/login/')
def escrow_status_overview(request):
    payments_list = Payment.objects.filter(
        customer=request.user
    ).select_related('booking', 'booking__package').order_by('-created_at')

    context = {'payments': payments_list}
    return render(request, 'customer/escrow_status.html', context)


@login_required(login_url='/auth/login/')
def earning_transaction(request):
    agent_payments = Payment.objects.filter(
        booking__package__agency=request.user
    ).select_related('booking', 'booking__user', 'booking__package', 'release_record').order_by('-created_at')
    
    released_payments = agent_payments.filter(escrow_status__iexact='released')
    total_earnings = released_payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    net_payable = Decimal('0.00')
    commission_deducted = Decimal('0.00')

    for payment in released_payments:
        if hasattr(payment, 'release_record') and payment.release_record:
            net_payable += payment.release_record.amount_released
            commission_deducted += payment.release_record.admin_commission_amount
        else:
            comm_rate = Decimal('10.00')
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
    ).exclude(status='refund_requested').select_related('package', 'user', 'payment').order_by('-created_at')
    
    status_filter = request.GET.get('status')
    if status_filter:
        bookings_list = bookings_list.filter(status=status_filter)
        
    search_query = request.GET.get('search')
    if search_query:
        bookings_list = bookings_list.filter(
            Q(id__icontains=search_query) | Q(user__username__icontains=search_query)
        )
        
    all_bookings = Bookings.objects.filter(package__agency=request.user).exclude(status='refund_requested')
    stats = {
        'total': all_bookings.count(),
        'pending': all_bookings.filter(status='pending').count(),
        'action_required': all_bookings.filter(status='action_required').count(),
        'visa_processing': all_bookings.filter(status='visa_processing').count(),
        'ticket_issued': all_bookings.filter(status='ticket_issued').count(),
        'cancel_requested': all_bookings.filter(status='cancel_requested').count(),
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

            send_booking_status_email(
                customer_email=booking.user.email,
                customer_name=booking.user.get_full_name() or booking.user.username,
                booking_id=booking.id,
                new_status="visa_processing",
                remarks="Visa processing has been started by your travel agent."
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

                Notification.objects.create(
                    recipient=booking.user,
                    title="Ticket Issued",
                    message=f"Ticket uploaded for Booking #{booking.id}. Please review and approve in your dashboard."
                )

                send_ticket_uploaded_notification(
                    customer_email=booking.user.email,
                    customer_name=booking.user.get_full_name() or booking.user.username,
                    booking_id=booking.id,
                    agent_name=request.user.get_full_name() or request.user.username
                )
                messages.success(request, "Ticket uploaded successfully.")

        elif action == "approve_cancellation":
            old_status = booking.status
            booking.status = "cancelled"
            booking.save()

            BookingStatusHistory.objects.create(
                booking=booking,
                old_status=old_status,
                new_status="cancelled",
                changed_by=request.user,
                comments="Cancellation approved by travel agent."
            )
            Notification.objects.create(
                recipient=booking.user,
                title="Booking Cancelled",
                message=f"Your cancellation request for Booking #{booking.id} has been approved."
            )

            send_booking_status_email(
                customer_email=booking.user.email,
                customer_name=booking.user.get_full_name() or booking.user.username,
                booking_id=booking.id,
                new_status="cancelled",
                remarks="Your cancellation request has been approved by the travel agency."
            )

            messages.success(request, f"Booking #{booking.id} marked as Cancelled.")

        elif action == "reject_cancellation":
            old_status = booking.status
            booking.status = "confirmed"
            booking.save()

            BookingStatusHistory.objects.create(
                booking=booking,
                old_status=old_status,
                new_status="confirmed",
                changed_by=request.user,
                comments="Cancellation request rejected by agent."
            )
            Notification.objects.create(
                recipient=booking.user,
                title="Cancellation Request Rejected",
                message=f"Your cancellation request for Booking #{booking.id} was rejected by the agent."
            )

            send_booking_status_email(
                customer_email=booking.user.email,
                customer_name=booking.user.get_full_name() or booking.user.username,
                booking_id=booking.id,
                new_status="confirmed",
                remarks="Cancellation request was rejected by the travel agent."
            )

            messages.warning(request, f"Cancellation request for Booking #{booking.id} rejected.")

    return redirect("stakeholder:booking_detail", booking_id=booking.pk)


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

            send_document_status_update_email(
                customer_email=booking.user.email,
                customer_name=customer.full_name,
                booking_id=booking.id,
                status="rejected",
                rejection_reason="Some submitted documents require correction or re-upload."
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

            send_document_status_update_email(
                customer_email=booking.user.email,
                customer_name=customer.full_name,
                booking_id=booking.id,
                status="approved"
            )

        customer.save()
        Notification.objects.create(
            recipient=booking.user,
            title="Document Verification Update",
            message=notif_msg
        )

        messages.success(request, f"Verification decisions saved for {customer.full_name}.")
        return redirect('stakeholder:booking_detail', booking_id=booking.id)


@login_required
def cancelled_booking(request):
    user = request.user

    cancelled_list = (
        Bookings.objects.filter(package__agency=user, status='cancelled')
        .select_related('user', 'package', 'payment')
        .order_by('-updated_at')
    )

    search_query = request.GET.get('q', '').strip()
    if search_query:
        cancelled_list = cancelled_list.filter(
            Q(id__icontains=search_query)
            | Q(user__username__icontains=search_query)
            | Q(user__first_name__icontains=search_query)
            | Q(user__last_name__icontains=search_query)
            | Q(user__email__icontains=search_query)
            | Q(package__name__icontains=search_query)
        )

    if request.user.email and request.GET.get('notify'):
        send_mail(
            subject="Safar-e-Haram: Cancelled Bookings Report",
            message=f"Hello {request.user.username},\n\nYou are viewing the updated list of cancelled bookings for your agency.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[request.user.email],
            fail_silently=True,
        )

    total_cancellations = cancelled_list.count()

    paginator = Paginator(cancelled_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'cancelled_booking': page_obj,
        'total_cancellations': total_cancellations,
        'search_query': search_query,
    }

    return render(request, 'stakeholder/cancelled_booking.html', context)


