import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

# Admin Email List (From settings.py or default fallback)
ADMIN_EMAILS = getattr(
    settings,
    "ADMIN_NOTIFICATION_EMAILS",
    ["safareharam.offcial1212@gmail.com"],
)


def send_custom_email(subject, recipient_list, template_name, context):
    """Generic Base Function to send HTML & Plain Text Emails Safely"""
    if not recipient_list:
        return False

    try:
        if isinstance(recipient_list, str):
            recipient_list = [recipient_list]

        # Clean duplicates and empty entries
        recipient_list = list(set([e for e in recipient_list if e]))

        if not recipient_list:
            return False

        html_content = render_to_string(template_name, context)
        text_content = strip_tags(html_content)

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=getattr(
                settings,
                "DEFAULT_FROM_EMAIL",
                "Safar-e-Haram Support <safareharam.offcial1212@gmail.com>",
            ),
            to=recipient_list,
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        return True
    except Exception as e:
        logger.error(f"Email sending failed: {str(e)}")
        return False


# ==============================================================================
# SECTION 1: ADMIN NOTIFICATION ALERTS (Admin ko milne wali emails)
# ==============================================================================

def send_password_change_email(user):
    subject = "Security Alert: Password Changed Successfully"
    message = f"Hello {user.username},\n\nYour account password has been changed successfully. If you did not make this change, please contact support immediately."
    
    # Direct text email
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
def send_admin_new_agent_alert(agent_name, agent_email, agency_name=""):
    """1. Naya Agent Jab Register/KYC Submit Kare"""
    context = {
        "agent_name": agent_name,
        "agent_email": agent_email,
        "agency_name": agency_name,
    }
    return send_custom_email(
        subject=f"ALERT: New Agent Registered - {agent_name}",
        recipient_list=ADMIN_EMAILS,
        template_name="emails/admin_new_agent_alert.html",
        context=context,
    )


def send_admin_new_package_alert(package_title, agent_name, price=""):
    """2. Agent Jab Naya Package Create Kare"""
    context = {
        "package_title": package_title,
        "agent_name": agent_name,
        "price": price,
    }
    return send_custom_email(
        subject=f"ALERT: New Package Created - {package_title}",
        recipient_list=ADMIN_EMAILS,
        template_name="emails/admin_new_package_alert.html",
        context=context,
    )


def send_admin_new_booking_alert(booking_id, customer_name, package_title, amount=""):
    """3. Customer Jab Nayi Booking Kare"""
    context = {
        "booking_id": booking_id,
        "customer_name": customer_name,
        "package_title": package_title,
        "amount": amount,
    }
    return send_custom_email(
        subject=f"ALERT: New Booking Received - #{booking_id}",
        recipient_list=ADMIN_EMAILS,
        template_name="emails/admin_new_booking_alert.html",
        context=context,
    )


def send_admin_refund_request_alert(booking_id, customer_name, amount="", reason=""):
    """4. Customer Refund ya Cancellation Request Bheje"""
    context = {
        "booking_id": booking_id,
        "customer_name": customer_name,
        "amount": amount,
        "reason": reason,
    }
    return send_custom_email(
        subject=f"ACTION REQUIRED: Refund Requested for Booking #{booking_id}",
        recipient_list=ADMIN_EMAILS,
        template_name="emails/admin_refund_request_alert.html",
        context=context,
    )


def send_complaint_submitted_emails(
    user_email, user_name, complaint_id, complaint_type, subject_text, description=""
):
    """5. Customer Complaint Submit Kare (Customer Confirmation + Admin Alert)"""
    context = {
        "user_name": user_name,
        "user_email": user_email,
        "complaint_id": complaint_id,
        "complaint_type": complaint_type,
        "subject_text": subject_text,
        "description": description,
    }
    
    # 1. Customer ko Confirmation Email
    send_custom_email(
        f"Complaint Received #{complaint_id} - Safar-e-Haram",
        [user_email],
        "emails/complaint_received_user.html",
        context,
    )
    
    # 2. Admin ko Immediate Alert Email
    return send_custom_email(
        f"ALERT: New Complaint Submitted #{complaint_id} by {user_name}",
        ADMIN_EMAILS,
        "emails/admin_complaint_alert.html",
        context,
    )


# ==============================================================================
# SECTION 2: AGENT NOTIFICATION EMAILS (Agent ko milne wali emails)
# ==============================================================================


def send_agent_account_status_email(agent_email, agent_name, is_approved, reason=""):
    """6. Admin Jab Agent Account Approve, Reject ya Rollback Kare"""
    context = {
        "agent_name": agent_name,
        "is_approved": is_approved,
        "reason": reason,
    }
    subject = (
        "Agent Account Approved - Safar-e-Haram"
        if is_approved
        else "Agent Account Verification Update - Safar-e-Haram"
    )
    return send_custom_email(
        subject, [agent_email], "emails/agent_account_status.html", context
    )


def send_new_booking_agent_notification(
    agent_email, agent_name, booking_id, package_title, customer_name
):
    """7. Agent ke Package par Nayi Booking Aaye"""
    context = {
        "agent_name": agent_name,
        "booking_id": booking_id,
        "package_title": package_title,
        "customer_name": customer_name,
    }
    return send_custom_email(
        f"New Booking Alert - #{booking_id} ({package_title})",
        [agent_email],
        "emails/agent_new_booking.html",
        context,
    )


def send_docs_resubmitted_email(customer_name, booking_id, agent_email=None):
    """8. Customer Document Dobara (Re-submit) Kare (Agent + Admin Alert)"""
    context = {"customer_name": customer_name, "booking_id": booking_id}
    recipients = ADMIN_EMAILS.copy()
    if agent_email:
        recipients.append(agent_email)

    return send_custom_email(
        f"ALERT: Documents Re-submitted for Booking #{booking_id}",
        recipients,
        "emails/docs_resubmitted_alert.html",
        context,
    )


def send_ticket_approved_notification(agent_email, customer_name, booking_id):
    """9. Customer Ticket Approve Kar De (Agent + Admin Alert)"""
    context = {"customer_name": customer_name, "booking_id": booking_id}
    recipients = [agent_email] + ADMIN_EMAILS if agent_email else ADMIN_EMAILS
    return send_custom_email(
        f"Ticket Approved by Customer - Booking #{booking_id}",
        recipients,
        "emails/ticket_approved_notice.html",
        context,
    )


def send_ticket_rejected_notification(agent_email, customer_name, booking_id, reason):
    """10. Customer Ticket Reject Kar De (Agent + Admin Alert)"""
    context = {
        "customer_name": customer_name,
        "booking_id": booking_id,
        "reason": reason,
    }
    recipients = [agent_email] + ADMIN_EMAILS if agent_email else ADMIN_EMAILS
    return send_custom_email(
        f"ACTION REQUIRED: Ticket Rejected by Customer - Booking #{booking_id}",
        recipients,
        "emails/ticket_rejected_notice.html",
        context,
    )


# ==============================================================================
# SECTION 3: CUSTOMER NOTIFICATION EMAILS (Customer ko milne wali emails)
# ==============================================================================


def send_booking_status_email(
    customer_email, customer_name, booking_id, new_status, remarks=""
):
    """11. Booking Status Change Ho (Confirmed, Completed, Cancelled, Pending)"""
    context = {
        "customer_name": customer_name,
        "booking_id": booking_id,
        "status": new_status,
        "remarks": remarks,
    }
    return send_custom_email(
        f"Booking Status Updated - #{booking_id} ({new_status.capitalize()})",
        [customer_email],
        "emails/booking_status_changed.html",
        context,
    )


def send_document_status_update_email(
    customer_email, customer_name, booking_id, status, rejection_reason=""
):
    """12. Uploaded Documents Status Update (Approved / Rejected by Agent)"""
    context = {
        "customer_name": customer_name,
        "booking_id": booking_id,
        "status": status,
        "rejection_reason": rejection_reason,
    }
    return send_custom_email(
        f"Document Verification Update - Booking #{booking_id}",
        [customer_email],
        "emails/customer_doc_status_update.html",
        context,
    )


def send_ticket_uploaded_notification(
    customer_email, customer_name, booking_id, agent_name
):
    """13. Agent Ticket Upload/Issue Kare"""
    context = {
        "customer_name": customer_name,
        "booking_id": booking_id,
        "agent_name": agent_name,
    }
    return send_custom_email(
        f"Ticket Issued for Booking #{booking_id} - Action Required",
        [customer_email],
        "emails/customer_ticket_uploaded.html",
        context,
    )


def send_booking_action_email(
    action_type,
    customer_email,
    customer_name,
    booking_id,
    agent_email=None,
    reason="",
    new_date="",
):
    """14. Customer ki Cancellation, Extension, ya Refund Action Update"""
    context = {
        "action_type": action_type,
        "customer_name": customer_name,
        "booking_id": booking_id,
        "reason": reason,
        "new_date": new_date,
    }

    subject_map = {
        "cancel": f"Booking Cancellation Requested - #{booking_id}",
        "refund": f"Refund Requested - Booking #{booking_id}",
        "extend": f"Date Extension Requested - Booking #{booking_id}",
    }

    # Customer Email
    send_custom_email(
        subject_map.get(action_type, f"Booking Action Request #{booking_id}"),
        [customer_email],
        "emails/customer_booking_action.html",
        context,
    )

    # Admin & Agent Alert
    admin_agent_recipients = ADMIN_EMAILS.copy()
    if agent_email:
        admin_agent_recipients.append(agent_email)

    return send_custom_email(
        f"ALERT: Customer Requested {action_type.capitalize()} for Booking #{booking_id}",
        admin_agent_recipients,
        "emails/admin_booking_action.html",
        context,
    )


# ==============================================================================
# SECTION 4: PAYMENT & ESCROW NOTIFICATION EMAILS
# ==============================================================================

def send_payment_escrow_held_email(customer_email, customer_name, booking_id, amount):
    """Triggered when customer submits payment and funds enter escrow."""
    context = {
        "customer_name": customer_name,
        "booking_id": booking_id,
        "amount": amount,
    }
    # 1. Email to Customer confirming funds are held in escrow
    send_custom_email(
        subject=f"Payment Received & Held in Escrow - Booking #{booking_id}",
        recipient_list=[customer_email],
        template_name="emails/customer_payment_escrow.html",
        context=context,
    )
    # 2. Admin Alert for new payment held in escrow
    return send_custom_email(
        subject=f"ALERT: New Escrow Payment Held - Booking #{booking_id}",
        recipient_list=ADMIN_EMAILS,
        template_name="emails/admin_payment_escrow.html",
        context=context,
    )


def send_payment_released_emails(customer_email, customer_name, agent_email, agent_name, booking_id, amount):
    """Triggered when Admin releases funds from escrow to the Agent."""
    context = {
        "customer_name": customer_name,
        "agent_name": agent_name,
        "booking_id": booking_id,
        "amount": amount,
    }

    # 1. Send confirmation to Customer
    send_custom_email(
        subject=f"Payment Released to Agent - Booking #{booking_id}",
        recipient_list=[customer_email],
        template_name="emails/customer_payment_released.html",
        context=context,
    )

    # 2. Send notification to Agent
    return send_custom_email(
        subject=f"Payout Released for Booking #{booking_id}",
        recipient_list=[agent_email],
        template_name="emails/agent_payout_released.html",
        context=context,
    )

from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

def get_admin_emails():
    """Helper function to fetch active superuser/admin email addresses."""
    admin_emails = list(
        User.objects.filter(is_superuser=True, is_active=True)
        .exclude(email='')
        .values_list('email', flat=True)
    )
    if not admin_emails and hasattr(settings, 'ADMINS') and settings.ADMINS:
        admin_emails = [email for _, email in settings.ADMINS]
    return admin_emails


def send_package_created_emails(user, package):
    """Send notification emails when a package is created."""
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')

    # 1. User Notification Email
    if user and user.email:
        send_mail(
            subject="Package Created Successfully",
            message=f"Hello {user.username},\n\nYour package '{package.name}' has been created successfully.",
            from_email=from_email,
            recipient_list=[user.email],
            fail_silently=True,
        )

    # 2. Admin Notification Email
    admin_emails = get_admin_emails()
    if admin_emails:
        creator_name = user.username if user and user.is_authenticated else "Unknown User"
        send_mail(
            subject=f"New Package Created: {package.name}",
            message=f"Admin Alert,\n\nA new package '{package.name}' has been created by {creator_name}.",
            from_email=from_email,
            recipient_list=admin_emails,
            fail_silently=True,
        )


def send_package_updated_emails(user, package):
    """Send notification emails when a package is updated."""
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')

    # 1. User Notification Email
    if user and user.email:
        send_mail(
            subject="Package Updated Successfully",
            message=f"Hello {user.username},\n\nYour package '{package.name}' has been updated successfully.",
            from_email=from_email,
            recipient_list=[user.email],
            fail_silently=True,
        )

    # 2. Admin Notification Email
    admin_emails = get_admin_emails()
    if admin_emails:
        updater_name = user.username if user and user.is_authenticated else "Unknown User"
        send_mail(
            subject=f"Package Updated: {package.name}",
            message=f"Admin Alert,\n\nThe package '{package.name}' (ID: {package.id}) was updated by {updater_name}.",
            from_email=from_email,
            recipient_list=admin_emails,
            fail_silently=True,
        )


def send_package_deleted_emails(user, package):
    """Send notification emails when a package status is changed to inactive/deleted."""
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')

    # 1. User Notification Email
    if user and user.email:
        send_mail(
            subject="Package Deactivated",
            message=f"Hello {user.username},\n\nYour package '{package.name}' status has been set to inactive.",
            from_email=from_email,
            recipient_list=[user.email],
            fail_silently=True,
        )

    # 2. Admin Notification Email
    admin_emails = get_admin_emails()
    if admin_emails:
        deleter_name = user.username if user and user.is_authenticated else "Unknown User"
        send_mail(
            subject=f"Package Deactivated: {package.name}",
            message=f"Admin Alert,\n\nThe package '{package.name}' (ID: {package.id}) was marked inactive by {deleter_name}.",
            from_email=from_email,
            recipient_list=admin_emails,
            fail_silently=True,
        )