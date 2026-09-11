import stripe
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.urls import reverse
from packages.models import Package
from payments.models import Payment, PaymentMethod, PaymentStatus
from payments import services
from .models import Bookings, BookingCustomers, Ticket, BookingStatusHistory

stripe.api_key = settings.STRIPE_SECRET_KEY

from django.db import transaction 

@login_required(login_url='/auth/login/')
@transaction.atomic
def book_package(request, package_id):
    package = get_object_or_404(Package.objects.select_for_update(), id=package_id)
    seats_left = package.seats_left()

    if package.status != 'active' or seats_left <= 0:
        messages.error(request, "this package is fully booked")
        return redirect('packages:package_list')

    if request.method == 'POST':
        names = request.POST.getlist('name_[]')
        submitted_count = len(names)
        try:
            form_person_count = int(request.POST.get('person_count', 1))
        except (ValueError, TypeError):
            form_person_count = 1

        person_count = submitted_count if submitted_count > 0 else form_person_count
        if person_count > seats_left:
            messages.error(request, f"In this package {seats_left} seats only available")
            return redirect(request.path)

        calculated_total = package.price * person_count
        booking = Bookings.objects.create(
            user=request.user,
            package=package,
            total_persons=person_count,
            total_amount=calculated_total,
            status='incomplete',
            customer_note=request.POST.get('customer_note', '')
        )

        phones = request.POST.getlist('phone_[]')
        cnics = request.POST.getlist('cnic_[]')
        emails = request.POST.getlist('email_[]')
        genders = request.POST.getlist('gender_[]')
        dobs = request.POST.getlist('dob_[]')
        addresses = request.POST.getlist('address_[]')
        passports = request.POST.getlist('passport_[]')
        issue_dates = request.POST.getlist('issue_date_[]')
        expiries = request.POST.getlist('expiry_[]')

        pass_files = request.FILES.getlist('pass_file_[]')
        digital_photos = request.FILES.getlist('digital_photo_[]')
        cnic_fronts = request.FILES.getlist('cnic_front_[]')
        cnic_backs = request.FILES.getlist('cnic_back_[]')

        for i in range(person_count):
            BookingCustomers.objects.create(
                booking=booking,
                full_name=names[i] if i < len(names) else '',
                phone_number=phones[i] if i < len(phones) else '',
                cnic=cnics[i] if i < len(cnics) else '',
                email=emails[i] if (i < len(emails) and emails[i]) else None,
                gender=genders[i] if (i < len(genders) and genders[i]) else None,
                date_of_birth=dobs[i] if (i < len(dobs) and dobs[i]) else None,
                address=addresses[i] if (i < len(addresses) and addresses[i]) else None,
                passport_number=passports[i] if (i < len(passports) and passports[i]) else None,
                passport_issue_date=issue_dates[i] if (i < len(issue_dates) and issue_dates[i]) else None,
                passport_expiry=expiries[i] if (i < len(expiries) and expiries[i]) else None,
                passport_scan=pass_files[i] if i < len(pass_files) else None,
                digital_photo=digital_photos[i] if i < len(digital_photos) else None,
                cnic_front=cnic_fronts[i] if i < len(cnic_fronts) else None,
                cnic_back=cnic_backs[i] if i < len(cnic_backs) else None,
                verification_status='pending'
            )

        package.booked_seats += person_count
        package.save()

        messages.success(request, "Booking request successfully submitted!")
        return redirect('bookings:choose_payment_method', booking_id=booking.id)

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
    if hasattr(booking, 'payment') and booking.payment.payment_status in [
        PaymentStatus.PAYMENT_VERIFIED, PaymentStatus.HELD_IN_ESCROW, PaymentStatus.RELEASED
    ]:
        return redirect('bookings:payment_status', booking_id=booking.id)

    if request.method == "POST":
        method = request.POST.get('payment_method')

        if method not in (PaymentMethod.STRIPE, PaymentMethod.RAAST):
            messages.error(request, "choose the correct payment method")
            return redirect('bookings:choose_payment_method', booking_id=booking.id)
        payment, created = Payment.objects.get_or_create(
            booking=booking,
            defaults={
                'customer': request.user,
                'agent': booking.package.agency,
                'payment_method': method,
                'amount': booking.total_amount,
                'payment_status': PaymentStatus.INCOMPLETE,
            }
        )
        if not created:
            payment.payment_method = method
            payment.amount = booking.total_amount
            payment.payment_status = PaymentStatus.INCOMPLETE
            payment.stripe_payment_intent_id = None  # Previous intent reset
            payment.save()

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
 
        booking.status = 'pending'
        booking.save()
    except ValueError as e:
        payment.payment_status = PaymentStatus.FAILED
        payment.save()
        booking.status = 'incomplete'
        booking.save()
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

    redirect_url = reverse('bookings:payment_status', kwargs={'booking_id': booking.id})
    return JsonResponse({'success': True, 'redirect_url': redirect_url})


@login_required(login_url='/auth/login/')
def retry_payment(request, booking_id):
    booking = get_object_or_404(Bookings, pk=booking_id, user=request.user)

    if hasattr(booking, 'payment'):
        payment = booking.payment
        payment.payment_status = PaymentStatus.INCOMPLETE
        payment.stripe_payment_intent_id = None
        payment.save()

    return redirect('bookings:choose_payment_method', booking_id=booking.id)


@login_required(login_url='/auth/login/')
def raast_payment_page(request, booking_id):
    booking = get_object_or_404(Bookings, pk=booking_id, user=request.user)
    payment = get_object_or_404(Payment, booking=booking, payment_method=PaymentMethod.RAAST)

    context = {
        'booking': booking,
        'payment': payment,
        'admin_raast_id': getattr(settings, "ADMIN_RAAST_ID", "03001234567"),
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
            messages.error(request, "Transaction ID enter karna zaroori hai.")
            return redirect('bookings:raast_payment', booking_id=booking.id)

        services.submit_raast_proof(
            payment,
            uploaded_by=request.user,
            screenshot=screenshot,
            transaction_reference=transaction_reference,
        )
        booking.status = 'pending'
        booking.save()

        messages.success(request, "Payment proof is submitted Admin ki wait for admin verfication.")
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