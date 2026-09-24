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
from .models import Bookings, BookingCustomers, Ticket, BookingStatusHistory, BookingChat
from notifications.models import Notification  
from datetime import datetime
stripe.api_key = settings.STRIPE_SECRET_KEY
from django.db import transaction 
from django.db.models import Q

def parse_date_safe(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None


@login_required(login_url='/auth/login/')
@transaction.atomic
def book_package(request, package_id):
    package = get_object_or_404(Package.objects.select_for_update(), id=package_id)
    seats_left = package.seats_left()

    if package.status != 'active' or seats_left <= 0:
        messages.error(request, "This package is fully booked.")
        return redirect('packages:package_list')

    if request.method == 'POST':
        try:
            names = request.POST.getlist('name_[]')
            submitted_count = len(names)

            try:
                form_person_count = int(request.POST.get('person_count', 1))
            except (ValueError, TypeError):
                form_person_count = 1

            person_count = submitted_count if submitted_count > 0 else form_person_count

            if person_count <= 0:
                messages.error(request, "Please enter a valid number of travelers.")
                return redirect(request.path)

            if person_count > seats_left:
                messages.error(request, f"In this package {seats_left} seats only available.")
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
                    date_of_birth=parse_date_safe(dobs[i] if i < len(dobs) else None),
                    address=addresses[i] if (i < len(addresses) and addresses[i]) else None,
                    passport_number=passports[i] if (i < len(passports) and passports[i]) else None,
                    passport_issue_date=parse_date_safe(issue_dates[i] if i < len(issue_dates) else None),
                    passport_expiry=parse_date_safe(expiries[i] if i < len(expiries) else None),
                    passport_scan=pass_files[i] if i < len(pass_files) else None,
                    digital_photo=digital_photos[i] if i < len(digital_photos) else None,
                    cnic_front=cnic_fronts[i] if i < len(cnic_fronts) else None,
                    cnic_back=cnic_backs[i] if i < len(cnic_backs) else None,
                    verification_status='pending'
                )

            package.booked_seats += person_count
            package.save()

        
            Notification.objects.create(
                recipient=request.user,
                sender=request.user,
                title="Booking Created",
                message=f"Your booking #{booking.id} for {package.name} has been successfully created.",
                notification_type='booking_created',
                priority='medium',
                redirect_url=f"/bookings/status/{booking.id}/",
                icon="fa-solid fa-bookmark"
            )
            if package.agency:
                Notification.objects.create(
                    recipient=package.agency,
                    sender=request.user,
                    title="New Booking Received",
                    message=f"You received a new booking #{booking.id} for package {package.name}.",
                    notification_type='agent_new_booking',
                    priority='high',
                    redirect_url=f"/agents/bookings/{booking.id}/",
                    icon="fa-solid fa-suitcase"
                )
            

            messages.success(request, "Booking request successfully submitted!")
            return redirect('bookings:choose_payment_method', booking_id=booking.id)

        except Exception as e:
            messages.error(request, f"Server Error: {str(e)}")
            return redirect(request.path)

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
        Notification.objects.create(
            recipient=request.user,
            sender=request.user,
            title="Payment Verified",
            message=f"Your Stripe payment for booking #{booking.id} has been verified.",
            notification_type='payment_verified',
            priority='high',
            redirect_url=f"/bookings/status/{booking.id}/",
            icon="fa-solid fa-check-circle"
        )
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
        Notification.objects.create(
            recipient=request.user,
            sender=request.user,
            title="Payment Proof Submitted",
            message=f"Your Raast payment proof for booking #{booking.id} has been submitted.",
            notification_type='payment_received',
            priority='medium',
            redirect_url=f"/bookings/status/{booking.id}/",
            icon="fa-solid fa-receipt"
        )
     

        messages.success(request, "Payment proof is submitted Admin wait for admin verfication.")
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

@login_required
def booking_chat(request, booking_id):
    booking = get_object_or_404(Bookings, id=booking_id)
    
    is_customer = (booking.user == request.user)
    is_agent = request.user.is_staff or getattr(booking.package, 'agency', None) == request.user
    
    if not (is_customer or is_agent):
        return redirect('home')
    
    # --- YAHAN CHANGE KAREIN (Loop method) ---
    unread_messages = booking.chats.filter(~Q(sender=request.user), is_read=False)
    for msg in unread_messages:
        msg.is_read = True
        msg.save()
    # ----------------------------------------
    
    chats = booking.chats.order_by('timestamp')
    
    if request.method == 'POST':
        message_text = request.POST.get('message')
        if message_text:
            BookingChat.objects.create(
                booking=booking,
                sender=request.user,
                message=message_text
            )
            
            # --- ADDED: Notification for New Chat Message ---
            recipient_user = booking.package.agency if request.user == booking.user else booking.user
            Notification.objects.create(
                recipient=recipient_user,
                sender=request.user,
                title=f"New Message on Booking #{booking.id}",
                message=f"{request.user.username} sent you a message.",
                notification_type='new_chat_message',
                priority='high',
                redirect_url=f"/bookings/chat/{booking.id}/",
                icon="fa-solid fa-comments"
            )
            # -----------------------------------------------

            return redirect('bookings:booking_chat', booking_id=booking.id)
               
    context = {'booking': booking, 'chats': chats}
    return render(request, 'customer/booking_chat.html', context)