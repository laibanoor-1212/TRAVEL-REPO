from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import KYCAgentForm
from .models import AgentKYC
from django.shortcuts import render, redirect
from django.contrib import messages
from packages.forms import PackageForm
from packages.models import Package
from packages.models import PackageType
from bookings.models import Bookings,BookingCustomers
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
        # HTML form se values extract karein (both duration and duration_days fallback)
        duration_val = request.POST.get('duration') or request.POST.get('duration_days')

        # Agar duration validation fail ho jaye toh default setup implement karein
        if not duration_val:
            duration_val = 15  # Model default value setup

        # Safe Object Creation matching all model attributes
        Package.objects.create(
            # Logged-in user ko directly agency ForeignKey assign karein
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
    # 1. Jis package ko edit karna hai usko database se nikala
    package = get_object_or_404(Package, pk=pk)
    
    # 🔴 SAB SE ZAROORI LINE: Jo types shell mein add ki thin, unhe yahan se fetch karna lazmi hai
    package_types = PackageType.objects.all() 

    if request.method == 'POST':
        package.name = request.POST.get('name')
        
        # Package Type update karne ka logic
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
        
        # Checkboxes logic
        package.visa = 'visa' in request.POST
        package.ticket = 'ticket' in request.POST
        package.transport = 'transport' in request.POST
        package.ziyarat = 'ziyarat' in request.POST

        if request.FILES.get('banner'):
            package.banner = request.FILES['banner']

        package.save()
        # Apne dashboard yamanage packages wale url ka sahi naam yahan likhein
        return redirect('stakeholder:manage-packages') 

  
    context = {
        'package': package,
        'package_types': package_types,
    }
    
    return render(request, 'stakeholder/edit_package.html', context)
def delete_package(request, pk):
    package = get_object_or_404(Package, pk=pk)
    
    # Security Check: (Optional)
    # if package.stakeholder != request.user.stakeholder_profile:
    #     return redirect('dashboard')
        
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

def payments(request):
    return render(request, 'stakeholder/payments.html')

def agent_complains(request):
    return render(request, 'stakeholder/agent_complains.html')

def cancelled_booking(request):
    return render(request, 'stakeholder/cancelled_booking.html')



