from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal

from .models import (
    Payment,
    PaymentProof,
    EscrowTransaction,
    PaymentRelease,
    PaymentStatusLog,
    PaymentStatus,
    CommissionSetting,
)


def _log_transition(payment, old_status, new_status, changed_by=None, notes=""):
    PaymentStatusLog.objects.create(
        payment=payment,
        old_status=old_status,
        new_status=new_status,
        changed_by=changed_by,
        notes=notes,
    )


def _set_status(payment, new_status, changed_by=None, notes=""):
    old_status = payment.payment_status
    payment.payment_status = new_status
    payment.save(update_fields=["payment_status", "updated_at"])
    _log_transition(payment, old_status, new_status, changed_by=changed_by, notes=notes)


def mark_stripe_payment_submitted(payment: Payment, stripe_payment_intent_id: str):
    if payment.payment_method != "stripe":
        raise ValueError("it is not stripe method payment")

    payment.stripe_payment_intent_id = stripe_payment_intent_id
    payment.save(update_fields=["stripe_payment_intent_id", "updated_at"])
    _set_status(payment, PaymentStatus.PAYMENT_SUBMITTED, notes="Stripe PaymentIntent created.")

    booking = payment.booking
    booking.status = "processing"
    booking.save(update_fields=["status"])


def verify_stripe_payment(payment: Payment, stripe_status: str):
    if payment.payment_method != "stripe":
        raise ValueError("It is  not stirpe method payment")

    if stripe_status != "succeeded":
        _set_status(payment, PaymentStatus.CANCELLED, notes=f"Stripe status: {stripe_status}")

        booking = payment.booking
        booking.status = "cancelled"
        booking.save(update_fields=["status"])

        return payment

    payment.paid_at = timezone.now()
    payment.save(update_fields=["paid_at", "updated_at"])
    _set_status(payment, PaymentStatus.PAYMENT_VERIFIED, notes="Auto-verified by Stripe Test Mode.")

    hold_in_escrow(payment)
    return payment


def submit_raast_proof(payment: Payment, uploaded_by, screenshot=None, transaction_reference=""):
    if payment.payment_method != "raast":
        raise ValueError("this  payment is not Raast method")

    proof = PaymentProof.objects.create(
        payment=payment,
        screenshot=screenshot,
        transaction_reference=transaction_reference,
        uploaded_by=uploaded_by,
    )
    payment.transaction_id = transaction_reference
    payment.save(update_fields=["transaction_id", "updated_at"])
    _set_status(payment, PaymentStatus.PAYMENT_SUBMITTED, changed_by=uploaded_by,
                notes="Raast proof uploaded, admin verification pending.")

    booking = payment.booking
    booking.status = "processing"
    booking.save(update_fields=["status"])

    return proof


def verify_raast_proof(proof: PaymentProof, verified_by):
    if not verified_by.is_staff:
        raise PermissionError("only admin can verify Raast payment")

    proof.is_verified = True
    proof.verified_by = verified_by
    proof.verified_at = timezone.now()
    proof.save(update_fields=["is_verified", "verified_by", "verified_at"])

    payment = proof.payment
    payment.paid_at = timezone.now()
    payment.save(update_fields=["paid_at", "updated_at"])
    _set_status(payment, PaymentStatus.PAYMENT_VERIFIED, changed_by=verified_by,
                notes="Raast proof manually verified by admin.")

    hold_in_escrow(payment)
    return payment


def reject_raast_proof(proof: PaymentProof, rejected_by, reason: str):
    if not rejected_by.is_staff:
        raise PermissionError(" only admin can proof ,reject")

    proof.is_verified = False
    proof.verified_by = rejected_by
    proof.verified_at = timezone.now()
    proof.rejection_reason = reason
    proof.save(update_fields=["is_verified", "verified_by", "verified_at", "rejection_reason"])

    payment = proof.payment
    _set_status(payment, PaymentStatus.PENDING, changed_by=rejected_by,
                notes=f"Raast proof rejected: {reason}")

    booking = payment.booking
    booking.status = "pending"
    booking.save(update_fields=["status"])

    return proof


@transaction.atomic
def hold_in_escrow(payment: Payment):
    if payment.payment_status != PaymentStatus.PAYMENT_VERIFIED:
        raise ValueError("Payment is not verified yet, do not hold in escrow.")

    EscrowTransaction.objects.get_or_create(
        payment=payment,
        defaults={"held_amount": payment.amount, "status": EscrowTransaction.Status.HELD},
    )
    payment.escrow_status = PaymentStatus.HELD_IN_ESCROW
    payment.save(update_fields=["escrow_status", "updated_at"])
    _set_status(payment, PaymentStatus.HELD_IN_ESCROW, notes="Funds held in escrow")

    booking = payment.booking
    booking.status = "processing"
    booking.save(update_fields=["status"])

    return payment


def mark_ticket_uploaded(payment: Payment):
    if payment.payment_status != PaymentStatus.HELD_IN_ESCROW:
        raise ValueError("before Escrow hold ticket upload is not valid")
    _set_status(payment, PaymentStatus.TICKET_UPLOADED, notes="Agent uploaded confirmed ticket")

    booking = payment.booking
    booking.status = "ticket_issued"
    booking.save(update_fields=["status"])

    return payment


def mark_customer_approved(payment: Payment, customer_user):
    booking = payment.booking
    if payment.payment_status != PaymentStatus.TICKET_UPLOADED:
        raise ValueError("before Ticket upload approval is not valid ")

    booking.customer_approved = True
    booking.customer_approved_at = timezone.now()
    booking.status = "confirmed"
    booking.save(update_fields=["customer_approved", "customer_approved_at", "status", "updated_at"])

    _set_status(payment, PaymentStatus.CUSTOMER_APPROVED, changed_by=customer_user,
                notes="Customer approved the ticket.")
    return payment




@transaction.atomic
def release_payment(payment: Payment, released_by_admin, release_notes: str = ""):
    if not released_by_admin.is_staff:
        raise PermissionError("Only admin can release payment.")

    if payment.escrow_status != PaymentStatus.HELD_IN_ESCROW:
        raise ValueError("Payment is not held in escrow; release is not possible.")

    # Ticket approval check (handles both direct booking field or ticket model relationship)
    ticket_approved = (
        getattr(payment.booking, 'customer_approved', False) or 
        (hasattr(payment.booking, 'ticket') and getattr(payment.booking.ticket, 'customer_approved', False))
    )
    if not ticket_approved:
        raise ValidationError("To release payment, ticket approval by the customer is mandatory.")

    if hasattr(payment, "release_record"):
        raise ValueError("This payment has already been released.")

    # 1. Fetch latest admin commission rate (Default to 10.00% if not set)
    comm_setting = CommissionSetting.objects.first()
    comm_rate = Decimal(str(comm_setting.commission_percentage)) if (comm_setting and comm_setting.commission_percentage is not None) else Decimal('10.00')

    # 2. Calculate Admin Commission & Net Released Amount
    gross_amount = Decimal(str(payment.amount))
    admin_commission = (gross_amount * comm_rate) / Decimal('100.00')
    net_released_amount = gross_amount - admin_commission

    raast_reference = ""
    if payment.payment_method == "raast":
        raast_reference = getattr(payment, 'agent_raast_id', '') or ""

    # 3. Create PaymentRelease Record with Commission Split
    PaymentRelease.objects.create(
        payment=payment,
        released_by=released_by_admin,
        amount_released=net_released_amount,
        admin_commission_amount=admin_commission,
        release_notes=release_notes,
        raast_payout_reference=raast_reference,
    )

    # 4. Update Payment Escrow Status
    payment.escrow_status = PaymentStatus.RELEASED
    payment.released_at = timezone.now()
    payment.released_by = released_by_admin
    payment.save(update_fields=["escrow_status", "released_at", "released_by", "updated_at"])

    # 5. Update Escrow Transaction Status
    if hasattr(payment, "escrow_transaction"):
        escrow_txn = payment.escrow_transaction
        escrow_txn.status = EscrowTransaction.Status.RELEASED
        escrow_txn.save(update_fields=["status", "updated_at"])

    _set_status(
        payment, 
        PaymentStatus.RELEASED, 
        changed_by=released_by_admin,
        notes=release_notes or f"Payment released by admin. (Commission: PKR {admin_commission})"
    )

    # 6. Mark Booking as Completed
    booking = payment.booking
    booking.status = "completed"
    booking.save(update_fields=["status", "updated_at"])

    return payment
def cancel_payment(payment: Payment, cancelled_by, reason: str = ""):
    if payment.payment_status == PaymentStatus.RELEASED:
        raise ValueError("Released payment is impossible to cancel.")
    _set_status(payment, PaymentStatus.CANCELLED, changed_by=cancelled_by, notes=reason)

    booking = payment.booking
    booking.status = "cancelled"
    booking.save(update_fields=["status"])

    return payment


def refund_payment(payment: Payment, refunded_by, reason: str = ""):
    if payment.payment_status == PaymentStatus.RELEASED:
        raise ValueError("Released payment is not possible to refund  — its a separate dispute process")
    if not refunded_by.is_staff:
        raise PermissionError("only admin process refund")

    if hasattr(payment, "escrow_transaction"):
        escrow_txn = payment.escrow_transaction
        escrow_txn.status = EscrowTransaction.Status.REFUNDED
        escrow_txn.save(update_fields=["status", "updated_at"])

    _set_status(payment, PaymentStatus.REFUNDED, changed_by=refunded_by, notes=reason)

    booking = payment.booking
    booking.status = "refunded"
    booking.save(update_fields=["status"])

    return payment