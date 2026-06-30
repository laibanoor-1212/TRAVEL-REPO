from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from packages.models import Package
from .models import Bookings, BookingCustomers


def book_package(request, package_id):
    # Database se automatic package dhoondna
    package = get_object_or_404(Package, id=package_id)
    
    if request.method == 'POST':
        # Form se total persons aur pricing details uthana
        person_count = int(request.POST.get('person_count', 1))
        calculated_total = package.price * person_count
        
        # Main Booking Model Save Karein
        booking = Bookings.objects.create(
            user=request.user,         # Booking karne wala customer/user
            package=package,           # Linked package jiski agency automatically track hogi
            total_persons=person_count,
            total_amount=calculated_total,
            status='pending'           # Default status
        )
        
        # HTML Form se Arrays/Lists uthana (Multiple travelers data)
        full_names = request.POST.getlist('name_[]')
        phone_numbers = request.POST.getlist('phone_[]')
        cnics = request.POST.getlist('cnic_[]')
        emails = request.POST.getlist('email_[]')
        addresses = request.POST.getlist('address_[]')
        passport_numbers = request.POST.getlist('passport_[]')
        passport_expiries = request.POST.getlist('expiry_[]')
        
        # Files upload matching
        passport_scans = request.FILES.getlist('pass_file_[]')
        passport_photos = request.FILES.getlist('photo_file_[]')
        cnic_fronts = request.FILES.getlist('cnic_front_[]')
        cnic_backs = request.FILES.getlist('cnic_back_[]')
        
        # Loop chala kar har customer ka data save karna
        for i in range(person_count):
            try:
                # Expiry date validation (agar empty ho to None jaye)
                expiry_date = passport_expiries[i] if (i < len(passport_expiries) and passport_expiries[i]) else None
                
                BookingCustomers.objects.create(
                    booking=booking,
                    full_name=full_names[i] if i < len(full_names) else '',
                    phone_number=phone_numbers[i] if i < len(phone_numbers) else '',
                    cnic=cnics[i] if i < len(cnics) else '',
                    email=emails[i] if i < len(emails) else '',
                    address=addresses[i] if i < len(addresses) else '',
                    passport_number=passport_numbers[i] if i < len(passport_numbers) else None,
                    passport_expiry=expiry_date,
                    
                    # Files saving
                    passport_scan=passport_scans[i] if i < len(passport_scans) else None,
                    passport_photo=passport_photos[i] if i < len(passport_photos) else None,
                    cnic_front=cnic_fronts[i] if i < len(cnic_fronts) else None,
                    cnic_back=cnic_backs[i] if i < len(cnic_backs) else None,
                )
            except Exception as e:
                print(f"Error saving traveler {i+1}: {e}")
        
        # Success Message
        booking_display_id = getattr(booking, 'booking_id', booking.id)
        messages.success(request, f"Booking #{booking_display_id} kamyabi se register ho gai hai!")
        
        return redirect('user_dashboard') 
        
    return render(request, 'bookings/booking.html', {'package': package})


 
def manage_bookings(request):
    # Database se sari Bookings nikalna (select_related query ko fast karta hai)
    bookings = Bookings.objects.all().select_related('user', 'package').order_by('-id')
    
    context = {
        'bookings': bookings
    }
    return render(request, 'stakeholder/manage_bookings.html', context)
