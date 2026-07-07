import uuid
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from stakeholder.models import AgentKYC
from bookings.models import Bookings
from packages.models import Package
from notifications.models import Notification

User = get_user_model()

def get_all_admins():
    return User.objects.filter(is_superuser=True)


@receiver(post_save, sender=User)
def handle_user_registration(sender, instance, created, **kwargs):
    if created:
        admins = get_all_admins()
        # FIX: CustomUser mein 'is_agent' field nahi hai, 'role' field hai
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
        elif status == 'rollback' or status == 'pending':
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


@receiver(post_save, sender=Package)
def handle_package_upload(sender, instance, created, **kwargs):
    if created:
        admins = get_all_admins()
        # FIX: Package model mein field 'agency' hai, 'agent' nahi
        agent_name = instance.agency.username if instance.agency else "System"

        for admin in admins:
            Notification.objects.create(
                recipient=admin,
                sender=instance.agency,
                title="New Package Uploaded",
                # FIX: Package model mein field 'name' hai, 'title' nahi
                message=f"Agent '{agent_name}' has uploaded a new package: '{instance.name}'.",
                notification_type='package_created',
                priority='medium',
                redirect_url=f"/adminpanel/packages/{instance.id}/",
                icon="fas fa-box-open"
            )


@receiver(post_save, sender=Bookings)
def handle_booking_signals(sender, instance, created, **kwargs):
    if created:
        admins = get_all_admins()
        customer = instance.user
        package = instance.package
        agent = package.agency if package else None

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
                # FIX: yahan bhi 'package.title' tha, 'package.name' hona chahiye
                message=f"Great news! '{customer.username}' has booked your package '{package.name}'.",
                notification_type='booking_pending',
                priority='high',
                redirect_url=f"/stakeholder/bookings/{instance.id}/",
                icon="fas fa-dollar-sign"
            )