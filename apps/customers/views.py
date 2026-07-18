from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from bookings.models import Bookings  
from .models import CustomerProfile
from adminpanel.models import Complaint
from payments.models import Payment
from bookings.models import Ticket 

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

@login_required(login_url='/auth/login/')
def user_bookings(request):
    current_user_bookings = Bookings.objects.filter(user=request.user).order_by('-created_at')
    context = {
        'bookings': current_user_bookings
    }
    return render(request, 'customer/user_booking.html', context)

@login_required(login_url='/auth/login/')
def user_dashboard(request):
    notifications = request.user.notifications.filter(is_deleted=False)[:10]
    unread_count = request.user.notifications.filter(is_read=False, is_deleted=False).count()

    context = {
        'notifications': notifications,
        'unread_count': unread_count,
    
    }
    return render(request, 'customer/user_layout.html', context)


def overview_user(request):
    return render(request,'customer/overview_user.html')
def customer_complaints(request):
    if request.method == "POST":
        complaint_type = request.POST.get('complaint_type')
        subject = request.POST.get('subject')
        description = request.POST.get('description')
        Complaint.objects.create(
            user=request.user,
            user_role='user',  
            complaint_type=complaint_type,
            subject=subject,
            description=description
        )
        return redirect('customers:customer_complaints') 
    customer_issues = [
        ('no_ticket', 'Flight Ticket Not Received Yet'),
        ('visa_delay', 'Visa Processing Delay / Document Issue'),
        ('passport_issue', 'Passport Return Issue'),
        ('wrong_billing', 'Incorrect Amount Charged'),
        ('transport_missing', 'Transport/Bus Not Arrived'),
        ('driver_behavior', 'Driver Misbehavior'),
        ('hotel_not_booked', 'Hotel Booking Not Found at Check-in'),
        ('room_quality', 'Room Quality/Amenities Not as Promised'),
        ('other', 'Other Issues / Emergency Assistance'),
    ]
    return render(request, 'customer/customer_complaints.html', {'issues': customer_issues})

@login_required(login_url='/auth/login/')
def escrow_status_overview(request):
    payments = Payment.objects.filter(
        customer=request.user
    ).select_related('booking', 'booking__package').order_by('-created_at')

    context = {'payments': payments}
    return render(request, 'customer/customer_escrow_status.html', context)


@login_required
def user_ticket(request):
    tickets = (
        Ticket.objects
        .filter(booking__user=request.user)
        .select_related('booking', 'booking__package', 'agent')
        .order_by('-uploaded_at')
    )
    return render(request, 'customer/user_ticket.html', {'tickets': tickets})
