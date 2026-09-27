import uuid
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.db.models import Q

# Project Models
from stakeholder.models import AgentKYC
from bookings.models import Bookings
from packages.models import Package
from notifications.models import Notification

# Dynamic Optional Imports (Errors se bachne ke liye)
try:
    from payments.models import Payment, PaymentProof
except ImportError:
    Payment, PaymentProof = None, None

try:
    from adminpanel.models import Complaint
except ImportError:
    try:
        from complaints.models import Complaint
    except ImportError:
        Complaint = None

try:
    from chat.models import Message
except ImportError:
    try:
        from chat.models import ChatMessage as Message
    except ImportError:
        Message = None

User = get_user_model()


def get_all_admins():
    """Helper: Sub superusers & admins fetch karne ke liye"""
    return User.objects.filter(Q(is_superuser=True) | Q(is_staff=True) | Q(role='admin'))


def track_previous_state(sender, instance, **kwargs):
    """Helper: Status updates tracking ke liye"""
    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            instance._old_status = getattr(
                old_instance, 'status', 
                getattr(old_instance, 'booking_status',
                getattr(old_instance, 'payment_status', 
                getattr(old_instance, 'kyc_status', None)))
            )
        except sender.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


# =============================================================
# 1. USER & AGENT REGISTRATION SIGNALS
# =============================================================
@receiver(post_save, sender=User)
def handle_user_registration(sender, instance, created, **kwargs):
    if created:
        admins = get_all_admins()
        is_agent = getattr(instance, 'role', 'user') == 'stakeholder'

        if is_agent:
            n_type = 'agent_registered'
            title = "New Agent Registered"
            message = f"Agent '{instance.username}' has registered and is awaiting verification."
            redirect_url = "/adminpanel/agents/"
        else:
            n_type = 'register'
            title = "New Customer Registration"
            message = f"Customer '{instance.username}' has successfully created an account."
            redirect_url = "/adminpanel/customers/"

        for admin in admins:
            Notification.objects.create(
                recipient=admin,
                sender=instance,
                title=title,
                message=message,
                notification_type=n_type,
                priority='medium',
                redirect_url=redirect_url,
                icon="fas fa-user-plus"
            )


# =============================================================
# 2. AGENT KYC SIGNALS
# =============================================================
@receiver(post_save, sender=AgentKYC)
def handle_kyc_signals(sender, instance, created, **kwargs):
    admins = get_all_admins()
    agent_user = instance.user

    if created:
        for admin in admins:
            Notification.objects.create(
                recipient=admin,
                sender=agent_user,
                title="New KYC Submitted",
                message=f"Agent '{agent_user.username}' has submitted their KYC documents.",
                notification_type='kyc_submitted',
                priority='high',
                redirect_url=f"/adminpanel/kyc/{instance.id}/",
                icon="fas fa-file-medical"
            )

    else:
        status = getattr(instance, 'kyc_status', 'pending')

        if status == 'approved':
            n_type = 'kyc_approved'
            title = "KYC Approved Successfully"
            message = "Congratulations! Your KYC documents have been verified. You can now upload packages."
            priority = 'high'
            icon = "fas fa-check-circle"
        elif status == 'rejected':
            n_type = 'kyc_rejected'
            title = "KYC Documents Rejected"
            message = "Your KYC verification failed. Please check the requirements and resubmit."
            priority = 'urgent'
            icon = "fas fa-times-circle"
        elif status in ['rollback', 'pending']:
            n_type = 'kyc_pending'
            title = "KYC Status: Action Required"
            message = "Your KYC has been rolled back. Please update the missing information."
            priority = 'medium'
            icon = "fas fa-undo"
        else:
            return

        Notification.objects.create(
            recipient=agent_user,
            sender=None,
            title=title,
            message=message,
            notification_type=n_type,
            priority=priority,
            redirect_url="/stakeholder/dashboard/",
            icon=icon
        )


# =============================================================
# 3. PACKAGE UPLOAD & STATUS SIGNALS
# =============================================================
@receiver(post_save, sender=Package)
def handle_package_upload(sender, instance, created, **kwargs):
    agent_user = getattr(instance, 'agency', None) or getattr(instance, 'agent', None)

    if created:
        admins = get_all_admins()
        agent_name = agent_user.username if agent_user else "System"

        for admin in admins:
            Notification.objects.create(
                recipient=admin,
                sender=agent_user,
                title="New Package Uploaded",
                message=f"Agent '{agent_name}' has uploaded a new package: '{instance.name}'.",
                notification_type='package_created',
                priority='medium',
                redirect_url=f"/adminpanel/packages/{instance.id}/",
                icon="fas fa-box-open"
            )


# =============================================================
# 4. BOOKING SIGNALS (New, Rollback, Cancelled)
# =============================================================
@receiver(pre_save, sender=Bookings)
def cache_booking_old_status(sender, instance, **kwargs):
    track_previous_state(sender, instance, **kwargs)


@receiver(post_save, sender=Bookings)
def handle_booking_signals(sender, instance, created, **kwargs):
    customer = instance.user
    package = instance.package
    agent = package.agency if package else None
    admins = get_all_admins()

    # 🟢 Event: New Booking Created
    if created:
        for admin in admins:
            Notification.objects.create(
                recipient=admin,
                sender=customer,
                title="New Package Booked",
                message=f"Customer '{customer.username}' booked '{package.name}'.",
                notification_type='booking_created',
                priority='high',
                redirect_url=f"/adminpanel/bookings/{instance.id}/",
                icon="fas fa-luggage-cart"
            )
        if agent:
            Notification.objects.create(
                recipient=agent,
                sender=customer,
                title="Your Package Has a New Booking!",
                message=f"Great news! '{customer.username}' has booked your package '{package.name}'.",
                notification_type='booking_pending',
                priority='high',
                redirect_url=f"/stakeholder/bookings/{instance.id}/",
                icon="fas fa-dollar-sign"
            )

    # 🔴 Event: Booking Status Updates (Rollback / Cancellation)
    else:
        old_status = getattr(instance, '_old_status', None)
        new_status = getattr(instance, 'status', getattr(instance, 'booking_status', None))

        if old_status != new_status:
            # Cancelled Booking -> Notify Agent & Admin
            if new_status in ['cancelled', 'cancelled_by_customer', 'cancelled_by_agent']:
                if agent:
                    Notification.objects.create(
                        recipient=agent,
                        sender=customer,
                        title=f"Booking #{instance.id} Cancelled",
                        message=f"Booking for '{package.name}' was cancelled.",
                        notification_type='booking_cancelled',
                        priority='high',
                        redirect_url=f"/stakeholder/bookings/{instance.id}/",
                        icon="fas fa-calendar-times"
                    )
                for admin in admins:
                    Notification.objects.create(
                        recipient=admin,
                        sender=customer or agent,
                        title=f"Booking #{instance.id} Cancelled",
                        message=f"Booking #{instance.id} for '{package.name}' has been cancelled.",
                        notification_type='booking_cancelled',
                        priority='high',
                        redirect_url=f"/adminpanel/bookings/{instance.id}/",
                        icon="fas fa-ban"
                    )

            # Booking Rollback by Agent -> Notify Customer
            elif new_status in ['rolled_back', 'rollback']:
                if customer:
                    Notification.objects.create(
                        recipient=customer,
                        sender=agent,
                        title=f"Booking #{instance.id} Rolled Back",
                        message=f"Your booking for '{package.name}' was rolled back by the agent. Refund process initiated.",
                        notification_type='booking_rollback',
                        priority='urgent',
                        redirect_url=f"/bookings/status/{instance.id}/",
                        icon="fas fa-undo-alt"
                    )


# =============================================================
# 5. PAYMENT & REFUND SIGNALS
# =============================================================
if Payment:
    @receiver(pre_save, sender=Payment)
    def cache_payment_old_status(sender, instance, **kwargs):
        track_previous_state(sender, instance, **kwargs)

    @receiver(post_save, sender=Payment)
    def handle_payment_signals(sender, instance, created, **kwargs):
        customer = getattr(instance, 'user', None) or getattr(instance, 'customer', None)
        agent = getattr(instance, 'agent', None)
        admins = get_all_admins()

        old_status = getattr(instance, '_old_status', None)
        new_status = getattr(instance, 'payment_status', getattr(instance, 'status', None))

        if not created and old_status != new_status:
            # Refund Requested -> Notify Admin & Agent
            if new_status in ['refund_requested', 'disputed']:
                for admin in admins:
                    Notification.objects.create(
                        recipient=admin,
                        sender=customer,
                        title=f"Refund Request for Booking #{instance.booking_id}",
                        message=f"Customer '{customer.username if customer else 'User'}' requested a refund for Payment #{instance.id}.",
                        notification_type='refund_requested',
                        priority='urgent',
                        redirect_url=f"/adminpanel/payments/{instance.id}/",
                        icon="fas fa-hand-holding-usd"
                    )
                if agent:
                    Notification.objects.create(
                        recipient=agent,
                        sender=customer,
                        title=f"Refund Claimed for Booking #{instance.booking_id}",
                        message=f"A refund was requested for Booking #{instance.booking_id}.",
                        notification_type='refund_requested',
                        priority='high',
                        redirect_url=f"/stakeholder/bookings/{instance.booking_id}/",
                        icon="fas fa-exclamation-triangle"
                    )

            # Refund Processed -> Notify Customer & Agent
            elif new_status == 'refunded':
                if customer:
                    Notification.objects.create(
                        recipient=customer,
                        sender=None,
                        title="Refund Approved",
                        message=f"Your refund for Booking #{instance.booking_id} has been processed successfully.",
                        notification_type='refund_approved',
                        priority='high',
                        redirect_url=f"/bookings/status/{instance.booking_id}/",
                        icon="fas fa-check-double"
                    )
                if agent:
                    Notification.objects.create(
                        recipient=agent,
                        sender=None,
                        title="Payment Refunded",
                        message=f"Payment for Booking #{instance.booking_id} was refunded back to customer.",
                        notification_type='payment_refunded',
                        priority='medium',
                        redirect_url=f"/stakeholder/bookings/{instance.booking_id}/",
                        icon="fas fa-receipt"
                    )


# =============================================================
# 6. PAYMENT PROOF SIGNALS (Verified / Rejected)
# =============================================================
if PaymentProof:
    @receiver(pre_save, sender=PaymentProof)
    def cache_proof_old_status(sender, instance, **kwargs):
        track_previous_state(sender, instance, **kwargs)

    @receiver(post_save, sender=PaymentProof)
    def handle_payment_proof_signals(sender, instance, created, **kwargs):
        old_status = getattr(instance, '_old_status', None)
        new_status = getattr(instance, 'status', None)

        if not created and old_status != new_status:
            payment = getattr(instance, 'payment', None)
            if payment:
                customer = getattr(payment, 'user', None) or getattr(payment, 'customer', None)
                agent = getattr(payment, 'agent', None)

                if new_status == 'verified':
                    if customer:
                        Notification.objects.create(
                            recipient=customer,
                            title="Payment Proof Verified",
                            message=f"Your payment proof for Booking #{payment.booking_id} was verified. Funds secured in Escrow.",
                            notification_type='payment_verified',
                            priority='medium',
                            redirect_url=f"/bookings/status/{payment.booking_id}/",
                            icon="fas fa-shield-alt"
                        )
                    if agent:
                        Notification.objects.create(
                            recipient=agent,
                            title="Escrow Payment Secured",
                            message=f"Payment for Booking #{payment.booking_id} is verified and held in escrow.",
                            notification_type='escrow_secured',
                            priority='medium',
                            redirect_url=f"/stakeholder/bookings/{payment.booking_id}/",
                            icon="fas fa-lock"
                        )
                elif new_status == 'rejected':
                    if customer:
                        Notification.objects.create(
                            recipient=customer,
                            title="Payment Proof Rejected",
                            message=f"Your payment receipt for Booking #{payment.booking_id} was rejected. Please upload valid proof.",
                            notification_type='payment_rejected',
                            priority='urgent',
                            redirect_url=f"/bookings/status/{payment.booking_id}/",
                            icon="fas fa-times-circle"
                        )


# =============================================================
# 7. CHAT MESSAGE SIGNALS (User <-> Stakeholder <-> Admin)
# =============================================================
if Message:
    @receiver(post_save, sender=Message)
    def handle_chat_message_signals(sender, instance, created, **kwargs):
        if created:
            sender_user = instance.sender
            recipient_user = getattr(instance, 'recipient', None) or getattr(instance, 'receiver', None)

            if recipient_user and recipient_user != sender_user:
                sender_name = sender_user.get_full_name() or sender_user.username
                Notification.objects.create(
                    recipient=recipient_user,
                    sender=sender_user,
                    title=f"New Message from {sender_name}",
                    message=instance.content[:60] + "..." if len(instance.content) > 60 else instance.content,
                    notification_type='chat_message',
                    priority='medium',
                    redirect_url=f"/chat/{getattr(instance, 'thread_id', '')}",
                    icon="fas fa-comments"
                )


# =============================================================
# 8. COMPLAINT SIGNALS
# =============================================================
if Complaint:
    @receiver(post_save, sender=Complaint)
    def handle_complaint_signals(sender, instance, created, **kwargs):
        customer = getattr(instance, 'user', None) or getattr(instance, 'customer', None)
        admins = get_all_admins()

        if created:
            for admin in admins:
                Notification.objects.create(
                    recipient=admin,
                    sender=customer,
                    title="New Complaint Filed",
                    message=f"New complaint filed by '{customer.username if customer else 'Customer'}'.",
                    notification_type='complaint_filed',
                    priority='high',
                    redirect_url=f"/adminpanel/complaints/{instance.id}/",
                    icon="fas fa-exclamation-circle"
                )