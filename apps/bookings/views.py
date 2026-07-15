import stripe
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from packages.models import Package
from .models import Bookings, BookingCustomers
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Bookings
from payments.models import Payment, PaymentMethod
from payments import services

stripe.api_key = settings.STRIPE_SECRET_KEY

def book_package(request, package_id):

    package = get_object_or_404(Package, id=package_id)
    
    if request.method == 'POST':
        person_count = int(request.POST.get('person_count', 1))
        calculated_total = package.price * person_count
        booking = Bookings.objects.create(
            user=request.user,        
            package=package,          
            total_persons=person_count,
            total_amount=calculated_total,
            status='pending'         
        )
        
       
        full_names = request.POST.getlist('name_[]')
        phone_numbers = request.POST.getlist('phone_[]')
        cnics = request.POST.getlist('cnic_[]')
        emails = request.POST.getlist('email_[]')
        addresses = request.POST.getlist('address_[]')
        passport_numbers = request.POST.getlist('passport_[]')
        passport_expiries = request.POST.getlist('expiry_[]')
        passport_scans = request.FILES.getlist('pass_file_[]')
        passport_photos = request.FILES.getlist('photo_file_[]')
        cnic_fronts = request.FILES.getlist('cnic_front_[]')
        cnic_backs = request.FILES.getlist('cnic_back_[]')
        
        for i in range(person_count):
            try:
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
        
         
        
    return render(request, 'bookings/booking.html', {'package': package})


 
def manage_bookings(request):
    # Database se sari Bookings nikalna (select_related query ko fast karta hai)
    bookings = Bookings.objects.all().select_related('user', 'package').order_by('-id')
    
    context = {
        'bookings': bookings
    }
    return render(request, 'stakeholder/manage_bookings.html', context)




@login_required(login_url='/auth/login/')
def choose_payment_method(request, booking_id):
    booking = get_object_or_404(Bookings, pk=booking_id, user=request.user)
    if hasattr(booking, 'payment'):
        return redirect('bookings:payment_status', booking_id=booking.id)

    if request.method == "POST":
        method = request.POST.get('payment_method')

        if method not in (PaymentMethod.STRIPE, PaymentMethod.RAAST):
            messages.error(request, "Sahi payment method choose karein.")
            return redirect('bookings:choose_payment_method', booking_id=booking.id)

        Payment.objects.create(
            booking=booking,
            customer=request.user,
            agent=booking.package.agency,
            payment_method=method,
            amount=booking.package.price,
        )

        if method == PaymentMethod.STRIPE:
            return redirect('bookings:stripe_checkout', booking_id=booking.id)
        else:
            return redirect('bookings:raast_payment', booking_id=booking.id)

    return render(request, 'bookings/choose_payment_method.html', {'booking': booking})


@login_required(login_url='/auth/login/')
def stripe_checkout_page(request, booking_id):
    booking = get_object_or_404(Bookings, pk=booking_id, user=request.user)
    payment = get_object_or_404(Payment, booking=booking, payment_method=PaymentMethod.STRIPE)

    if not payment.stripe_payment_intent_id:
        intent = stripe.PaymentIntent.create(
            amount=int(payment.amount * 100), 
            currency="pkr",
            metadata={"booking_id": booking.id, "payment_id": payment.id},
        )
        services.mark_stripe_payment_submitted(payment, stripe_payment_intent_id=intent.id)
        client_secret = intent.client_secret
    else:
        intent = stripe.PaymentIntent.retrieve(payment.stripe_payment_intent_id)
        client_secret = intent.client_secret

    context = {
        'booking': booking,
        'payment': payment,
        'client_secret': client_secret,
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
    }
    return render(request, 'bookings/stripe_checkout.html', context)


@login_required(login_url='/auth/login/')
def confirm_stripe_payment(request, booking_id):
    """Stripe.js se payment confirm hone ke baad frontend ye endpoint call karega (AJAX)."""
    booking = get_object_or_404(Bookings, pk=booking_id, user=request.user)
    payment = get_object_or_404(Payment, booking=booking, payment_method=PaymentMethod.STRIPE)

    intent = stripe.PaymentIntent.retrieve(payment.stripe_payment_intent_id)

    try:
        services.verify_stripe_payment(payment, stripe_status=intent.status)
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

    return JsonResponse({'success': True, 'redirect_url': f'/bookings/{booking.id}/payment-status/'})


@login_required(login_url='/auth/login/')
def raast_payment_page(request, booking_id):
    booking = get_object_or_404(Bookings, pk=booking_id, user=request.user)
    payment = get_object_or_404(Payment, booking=booking, payment_method=PaymentMethod.RAAST)

    context = {
        'booking': booking,
        'payment': payment,
        'admin_raast_id': getattr(settings, "ADMIN_RAAST_ID", "Not configured"),
    }
    return render(request, 'bookings/raast_payment.html', context)


@login_required(login_url='/auth/login/')
def upload_raast_proof(request, booking_id):
    booking = get_object_or_404(Bookings, pk=booking_id, user=request.user)
    payment = get_object_or_404(Payment, booking=booking, payment_method=PaymentMethod.RAAST)

    if request.method == "POST":
        transaction_reference = request.POST.get('transaction_reference')
        screenshot = request.FILES.get('screenshot')

        if not transaction_reference:
            messages.error(request, "Transaction ID daalna zaroori hai.")
            return redirect('bookings:raast_payment', booking_id=booking.id)

        services.submit_raast_proof(
            payment,
            uploaded_by=request.user,
            screenshot=screenshot,
            transaction_reference=transaction_reference,
        )
        messages.success(request, "Proof submit ho gayi, admin verification ka wait karein.")
        return redirect('bookings:payment_status', booking_id=booking.id)

    return redirect('bookings:raast_payment', booking_id=booking.id)


@login_required(login_url='/auth/login/')
def payment_status_view(request, booking_id):
    booking = get_object_or_404(Bookings, pk=booking_id, user=request.user)
    payment = getattr(booking, 'payment', None)
    ticket = getattr(booking, 'ticket', None)

    context = {
        'booking': booking,
        'payment': payment,
        'ticket': ticket,
    }
    return render(request, 'bookings/payment_status.html', context)

@login_required(login_url='/auth/login/')
def approve_ticket_view(request, booking_id):
    booking = get_object_or_404(Bookings, pk=booking_id, user=request.user)
    payment = get_object_or_404(Payment, booking=booking)

    if request.method == "POST":
        try:
            services.mark_customer_approved(payment, customer_user=request.user)
            messages.success(request, "Ticket approve ho gaya, admin payment release kar dega.")
        except ValueError as e:
            messages.error(request, f"Approve nahi hua: {e}")

    return redirect('bookings:payment_status', booking_id=booking.id)
