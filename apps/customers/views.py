from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from bookings.models import Bookings  # Ya jahan bhi aapka Bookings model hai

@login_required
def user_bookings(request):
    # '-booking_date' ki jagah '-created_at' use karein
    current_user_bookings = Bookings.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'bookings': current_user_bookings
    }
    return render(request, 'customer/user_booking.html', context)
def customer_kyc(request):
    return render(request,'customer/customer_kyc.html')
def user_dashboard(request):
    return render(request,'customer/user_layout.html')


