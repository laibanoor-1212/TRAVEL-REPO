import stripe
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from packages.models import Package
from .models import Bookings, BookingCustomers
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import Bookings, Ticket 
from packages.models import Package
from django.urls import reverse
from payments.models import Payment, PaymentMethod
from payments import services

stripe.api_key = settings.STRIPE_SECRET_KEY



@login_required
def book_package(request, package_id):
    package = get_object_or_404(Package, id=package_id)

    if request.method == 'POST':
        person_count = int(request.POST.get('person_count', 1))
        calculated_total = package.price * person_count

        # 1. Main Booking Record Create Karein
        booking = Bookings.objects.create(
            user=request.user,
            package=package,
            total_persons=person_count,
            total_amount=calculated_total,
            status='pending',
            customer_note=request.POST.get('customer_note', '')
        )

        # 2. Travelers List Data Extract Karein
        names = request.POST.getlist('name_[]')
        phones = request.POST.getlist('phone_[]')
        cnics = request.POST.getlist('cnic_[]')
        emails = request.POST.getlist('email_[]')
        addresses = request.POST.getlist('address_[]')
        passports = request.POST.getlist('passport_[]')
        expiries = request.POST.getlist('expiry_[]')

        pass_files = request.FILES.getlist('pass_file_[]')
        photo_files = request.FILES.getlist('photo_file_[]')
        cnic_fronts = request.FILES.getlist('cnic_front_[]')
        cnic_backs = request.FILES.getlist('cnic_back_[]')

        # 3. Create BookingCustomers Instances
        for i in range(len(names)):
            BookingCustomers.objects.create(
                booking=booking,
                full_name=names[i],
                phone_number=phones[i] if i < len(phones) else '',
                cnic=cnics[i] if i < len(cnics) else '',
                email=emails[i] if (i < len(emails) and emails[i]) else None,
                address=addresses[i] if (i < len(addresses) and addresses[i]) else None,
                passport_number=passports[i] if (i < len(passports) and passports[i]) else None,
                passport_expiry=expiries[i] if (i < len(expiries) and expiries[i]) else None,
                passport_scan=pass_files[i] if i < len(pass_files) else None,
                passport_photo=photo_files[i] if i < len(photo_files) else None,
                cnic_front=cnic_fronts[i] if i < len(cnic_fronts) else None,
                cnic_back=cnic_backs[i] if i < len(cnic_backs) else None,
                verification_status='pending'
            )

        messages.success(request, "Booking request submitted successfully!")
        # Redirect using booking slug
        return redirect('bookings:booking_success', slug=booking.slug)

    return render(request, 'bookings/booking.html', {'package': package})


@login_required
def booking_success(request, slug):
    booking = get_object_or_404(Bookings, slug=slug, user=request.user)
    return render(request, 'bookings/booking_success.html', {'booking': booking})


 
def manage_bookings(request):
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
    booking = get_object_or_404(Bookings, pk=booking_id, user=request.user)
    payment = get_object_or_404(Payment, booking=booking, payment_method=PaymentMethod.STRIPE)

    intent = stripe.PaymentIntent.retrieve(payment.stripe_payment_intent_id)

    try:
        services.verify_stripe_payment(payment, stripe_status=intent.status)
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

    redirect_url = reverse('bookings:payment_status', kwargs={'booking_id': booking.id})
    return JsonResponse({'success': True, 'redirect_url': redirect_url})
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
            messages.error(request, "Transaction ID is mandatory.")
            return redirect('bookings:raast_payment', booking_id=booking.id)

        services.submit_raast_proof(
            payment,
            uploaded_by=request.user,
            screenshot=screenshot,
            transaction_reference=transaction_reference,
        )
        messages.success(request, "Proof is submitted, wait for admin verification.")
        return redirect('bookings:payment_status', booking_id=booking.id)

    return redirect('bookings:raast_payment', booking_id=booking.id)


@login_required(login_url='/auth/login/')
def payment_status(request, booking_id):
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
def edit_booking_documents(request, booking_id):
    """ Customer side view to update rejected customer details after rollback """
    booking = get_object_or_404(Bookings, pk=booking_id, user=request.user)
    customers = booking.CustomerProfile.all()

    if request.method == 'POST':
        for cust in customers:
            if cust.verification_status == 'rejected':
                cust.full_name = request.POST.get(f'full_name_{cust.id}', cust.full_name)
                cust.passport_number = request.POST.get(f'passport_number_{cust.id}', cust.passport_number)

                if request.FILES.get(f'passport_scan_{cust.id}'):
                    cust.passport_scan = request.FILES[f'passport_scan_{cust.id}']
                if request.FILES.get(f'passport_photo_{cust.id}'):
                    cust.passport_photo = request.FILES[f'passport_photo_{cust.id}']
                if request.FILES.get(f'cnic_front_{cust.id}'):
                    cust.cnic_front = request.FILES[f'cnic_front_{cust.id}']
                if request.FILES.get(f'cnic_back_{cust.id}'):
                    cust.cnic_back = request.FILES[f'cnic_back_{cust.id}']

                cust.verification_status = 'pending'
                cust.rejection_reason = ''
                cust.save()

        old_status = booking.status
        booking.status = 'processing'
        booking.save()

        BookingStatusHistory.objects.create(
            booking=booking,
            old_status=old_status,
            new_status='processing',
            changed_by=request.user,
            remarks="Customer resubmitted details after rollback."
        )

        messages.success(request, "Documents successfully resubmit ho gaye hain.")
        return redirect('bookings:payment_status', booking_id=booking.id)

    return render(request, 'bookings/edit_booking.html', {'booking': booking, 'customers': customers})



