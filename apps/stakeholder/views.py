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
from django.shortcuts import redirect, get_object_or_404


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
            obj.kyc_status = 'pending'   # only when user submits new KYC

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

    return render(request, 'stakeholder/agent_details.html', {
        'agentkyc': agentkyc
    })
@login_required(login_url='/accounts/login/')
def account_locked(request):
    agentkyc = AgentKYC.objects.filter(user=request.user).first()

    return render(request, 'stakeholder/account_locked.html', {
        'agentkyc': agentkyc
    })


def create_packages(request):
    package_types = PackageType.objects.filter(is_active=True)

    if request.method == "POST":
        duration_val = request.POST.get('duration') or request.POST.get('duration_days')
        if not duration_val:
            duration_val = 15  
        Package.objects.create(
            agency=request.user,
            name=request.POST.get('name'),
            package_type_id=request.POST.get('package_type'),
            tier=request.POST.get('tier', 'standard'),
            country=request.POST.get('country', 'Saudi Arabia'),
            city=request.POST.get('city', 'Makkah'),
            price=request.POST.get('price') or 100000,
            total_seats=request.POST.get('total_seats') or 50,
            departure_date=request.POST.get('departure_date') or None,
            application_deadline=request.POST.get('application_deadline') or None,
            
            # Duration & Accommodation Specifications
            duration_days=duration_val,
            makkah_hotel=request.POST.get('makkah_hotel', 'Standard Hotel'),
            madinah_hotel=request.POST.get('madinah_hotel', 'Standard Hotel'),
            
            # Checkbox values extraction (True/False checks)
            visa=request.POST.get('visa') == 'on',
            ticket=request.POST.get('ticket') == 'on',
            transport=request.POST.get('transport') == 'on',
            ziyarat=request.POST.get('ziyarat') == 'on',
            
            description=request.POST.get('description', 'Package details coming soon...'),
            banner=request.FILES.get('banner') if request.FILES.get('banner') else 'package_banners/default.jpg',
            status=request.POST.get('status', 'active'),
        )

        messages.success(request, "Package created successfully.")
        return redirect('stakeholder:manage_packages')

    return render(
        request,
        'stakeholder/create_packages.html',
        {'package_types': package_types}
    )

def update_package(request, pk):
    package = get_object_or_404(Package, pk=pk)
    package_types = PackageType.objects.all() 

    if request.method == 'POST':
        package.name = request.POST.get('name')
        type_id = request.POST.get('package_type')
        if type_id:
            package.package_type_id = type_id
            
        package.tier = request.POST.get('tier')
        package.country = request.POST.get('country')
        package.city = request.POST.get('city')
        package.price = request.POST.get('price')
        package.total_seats = request.POST.get('total_seats')
        package.duration_days = request.POST.get('duration_days')
        package.departure_date = request.POST.get('departure_date')
        package.application_deadline = request.POST.get('application_deadline')
        package.makkah_hotel = request.POST.get('makkah_hotel')
        package.madinah_hotel = request.POST.get('madinah_hotel')
        package.visa = 'visa' in request.POST
        package.ticket = 'ticket' in request.POST
        package.transport = 'transport' in request.POST
        package.ziyarat = 'ziyarat' in request.POST

        if request.FILES.get('banner'):
            package.banner = request.FILES['banner']

        package.save()
        return redirect('stakeholder:manage-packages') 

  
    context = {
        'package': package,
        'package_types': package_types,
    }
    
    return render(request, 'stakeholder/edit_package.html', context)
def delete_package(request, pk):
    package = get_object_or_404(Package, pk=pk)  
    package.delete()
    messages.success(request, "Package deleted successfully!")
    return redirect('packages:manage_packages')

def manage_packages(request):
   
    active_packages = Package.objects.filter(status='active').order_by('-created_at')
    inactive_packages = Package.objects.exclude(status='active').order_by('-created_at')

    return render(
        request,
        'stakeholder/manage_packages.html',
        {
            'active_packages': active_packages,
            'inactive_packages': inactive_packages,
        }
    )

@login_required(login_url='/auth/login/')
def stakeholder_dashboard(request):
   
    agent_bookings = Bookings.objects.filter(package__agency=request.user).order_by('-id')
    date_requests = [] 
    
    context = {
        'bookings': agent_bookings,
        'date_requests': date_requests,
    }
    return render(request, 'stakeholder/stakeholder_dashboard.html', context)

@login_required(login_url='/auth/login/')
def stakeholder_dashboard(request):

    agent_bookings = Bookings.objects.filter(package__agency=request.user).order_by('-id')
    date_requests = [] 

    notifications = request.user.notifications.filter(is_deleted=False)[:10]
    unread_count = request.user.notifications.filter(is_read=False, is_deleted=False).count()

    context = {
        'bookings': agent_bookings,
        'date_requests': date_requests,
        
        'notifications': notifications,
        'unread_count': unread_count,
    }
    return render(request, 'stakeholder/stakeholder_dashboard.html', context)


@login_required(login_url='/auth/login/')
def manage_booking(request):
    all_bookings_count = Bookings.objects.count()
    print(f"--- DEBUG: Total bookings in DB: {all_bookings_count} ---")
    print(f"--- DEBUG: Logged in Travel Agent: {request.user.email} ---")
    
    
    bookings = Bookings.objects.filter(package__agency=request.user).select_related('user', 'package').order_by('-id')
    
    print(f"--- DEBUG: Bookings found for this Agent: {bookings.count()} ---")

    context = {
        'bookings': bookings
    }
  
    return render(request, 'stakeholder/manage_booking.html', context)
@login_required(login_url='/auth/login/')
def booking_detail_view(request, booking_id): 
   
    booking = get_object_or_404(Bookings, id=booking_id, package__agency=request.user)
    
    travelers = BookingCustomers.objects.filter(booking=booking)
    
    context = {
        'booking': booking,
        'travelers': travelers,
    }
    return render(request, 'stakeholder/booking_detail.html', context)
def earning_transaction(request):
    return render(request, 'stakeholder/earning_transaction.html')


def agent_complaints(request):
    if request.method == "POST":
        complaint_type = request.POST.get('complaint_type')
        subject = request.POST.get('subject')
        description = request.POST.get('description')
        Complaint.objects.create(
            user=request.user,
            user_role='stakeholder',  
            complaint_type=complaint_type,
            subject=subject,
            description=description
        )
        return redirect('stakeholder:agent_complaints') 
 
    agent_issues = [
        ('no_payment', 'Payment Pending / Commission Not Received'),
        ('info_not_sent', 'Customer Data Not Forwarded to Supplier'),
        ('portal_error', 'Web App Technical Error / System Crash'),
        ('visa_delay', 'Visa Processing Issues for Group'),
        ('other', 'Other Operational Issues'),
    ]
    return render(request, 'stakeholder/agent_complaints.html', {'issues': agent_issues})

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
        escrow_status__in=['held_in_escrow', 'released']   # <-- sirf escrow tak pohanchi hui payments
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
            messages.success(request, "ticket upload wait kar the customer approval.")
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