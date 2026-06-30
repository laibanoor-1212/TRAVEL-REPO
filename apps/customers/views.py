from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from bookings.models import Bookings  
from .models import CustomerProfile
from notifications.models import Notification

@login_required(login_url='/accounts/login/')
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
        
        # Checkboxes handling (interested_packages)
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


@login_required(login_url='/accounts/login/')
def customer_kyc(request):
    # Agar profile database mein pehle se hai toh utha lo, nahi toh safe error handling karo
    try:
        profile = CustomerProfile.objects.get(user=request.user)
    except CustomerProfile.DoesNotExist:
        profile = CustomerProfile(user=request.user)  # Sirf memory mein object banaya hai, save nahi kiya abhi

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
        profile.cnic_number = request.POST.get('cnic_number') or None  # Empty string ki jagah NULL save hoga
        
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
        profile.save()  # Idhar profile database mein insert/update ho jaye gi bina duplicate key error ke
        return redirect('customers:user_dashboard') 
        
    # GET request par template ko profile pass karein (chahe woh khali ho ya database se aayi ho)
    return render(request, 'customer/customer_kyc.html', {'profile': profile})


def user_bookings(request):
    current_user_bookings = Bookings.objects.filter(user=request.user).order_by('-created_at')
    context = {
        'bookings': current_user_bookings
    }
    return render(request, 'customer/user_booking.html', context)

@login_required(login_url='/accounts/login/')
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