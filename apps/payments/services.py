"""
payments/services.py
======================
Escrow ki poori business logic yahan hai. Views ya admin actions kabhi
bhi payment.payment_status ko directly set NAHI karenge — hamesha ye
functions call karenge. Isse:
  - Har transition PaymentStatusLog mein audit ho jati hai
  - Invalid transitions (jaise approval se pehle release) yahin rukte hain
  - Gateway (Stripe/Raast) ka logic escrow rules se alag rehta hai
"""

from django.db import transaction
from django.utils import timezone

from .models import (
    Payment,
    PaymentProof,
    EscrowTransaction,
    PaymentRelease,
    PaymentStatusLog,
    PaymentStatus,
)


# ---------------------------------------------------------------------
# Internal helper — audit log likhna kabhi mat bhoolna
# ---------------------------------------------------------------------

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


# ---------------------------------------------------------------------
# 1. Stripe — auto verification (Test Mode)
# ---------------------------------------------------------------------

def mark_stripe_payment_submitted(payment: Payment, stripe_payment_intent_id: str):
    """Stripe se PaymentIntent create hote hi call karein."""
    if payment.payment_method != "stripe":
        raise ValueError("Ye payment Stripe method ki nahi hai.")

    payment.stripe_payment_intent_id = stripe_payment_intent_id
    payment.save(update_fields=["stripe_payment_intent_id", "updated_at"])
    _set_status(payment, PaymentStatus.PAYMENT_SUBMITTED, notes="Stripe PaymentIntent created.")


def verify_stripe_payment(payment: Payment, stripe_status: str):
    """
    Stripe se webhook/confirmation aane ke baad call karein.
    stripe_status: Stripe se aaya hua status (e.g. 'succeeded').
    """
    if payment.payment_method != "stripe":
        raise ValueError("Ye payment Stripe method ki nahi hai.")

    if stripe_status != "succeeded":
        _set_status(payment, PaymentStatus.CANCELLED, notes=f"Stripe status: {stripe_status}")
        return payment

    payment.paid_at = timezone.now()
    payment.save(update_fields=["paid_at", "updated_at"])
    _set_status(payment, PaymentStatus.PAYMENT_VERIFIED, notes="Auto-verified by Stripe Test Mode.")

    # Stripe verify hote hi seedha escrow mein hold ho jata hai
    hold_in_escrow(payment)
    return payment


# ---------------------------------------------------------------------
# 2. Raast — manual verification via proof upload
# ---------------------------------------------------------------------

def submit_raast_proof(payment: Payment, uploaded_by, screenshot=None, transaction_reference=""):
    """Customer proof upload karta hai — admin verification ka wait shuru hota hai."""
    if payment.payment_method != "raast":
        raise ValueError("Ye payment Raast method ki nahi hai.")

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
    return proof


def verify_raast_proof(proof: PaymentProof, verified_by):
    """Sirf admin (is_staff) call kar sakta hai."""
    if not verified_by.is_staff:
        raise PermissionError("Sirf admin Raast payment verify kar sakta hai.")

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
    """Fake/invalid proof — admin reject karta hai, customer ko dobara upload karna hoga."""
    if not rejected_by.is_staff:
        raise PermissionError("Sirf admin proof reject kar sakta hai.")

    proof.is_verified = False
    proof.verified_by = rejected_by
    proof.verified_at = timezone.now()
    proof.rejection_reason = reason
    proof.save(update_fields=["is_verified", "verified_by", "verified_at", "rejection_reason"])

    payment = proof.payment
    _set_status(payment, PaymentStatus.PENDING, changed_by=rejected_by,
                notes=f"Raast proof rejected: {reason}")
    return proof


# ---------------------------------------------------------------------
# 3. Hold in Escrow — dono methods (Stripe/Raast) ke liye common step
# ---------------------------------------------------------------------

@transaction.atomic
def hold_in_escrow(payment: Payment):
    if payment.payment_status != PaymentStatus.PAYMENT_VERIFIED:
        raise ValueError("Payment abhi verified nahi hai, escrow mein hold nahi ho sakta.")

    EscrowTransaction.objects.get_or_create(
        payment=payment,
        defaults={"held_amount": payment.amount, "status": EscrowTransaction.Status.HELD},
    )
    payment.escrow_status = PaymentStatus.HELD_IN_ESCROW
    payment.save(update_fields=["escrow_status", "updated_at"])
    _set_status(payment, PaymentStatus.HELD_IN_ESCROW, notes="Funds held in escrow.")
    return payment


# ---------------------------------------------------------------------
# 4. Ticket upload + customer approval (booking app se call hoga)
# ---------------------------------------------------------------------

def mark_ticket_uploaded(payment: Payment):
    if payment.payment_status != PaymentStatus.HELD_IN_ESCROW:
        raise ValueError("Escrow hold hone se pehle ticket upload valid nahi.")
    _set_status(payment, PaymentStatus.TICKET_UPLOADED, notes="Agent uploaded confirmed ticket.")
    return payment


def mark_customer_approved(payment: Payment, customer_user):
    booking = payment.booking
    if payment.payment_status != PaymentStatus.TICKET_UPLOADED:
        raise ValueError("Ticket upload hone se pehle approval valid nahi.")

    booking.customer_approved = True
    booking.customer_approved_at = timezone.now()
    booking.save(update_fields=["customer_approved", "customer_approved_at", "updated_at"])

    _set_status(payment, PaymentStatus.CUSTOMER_APPROVED, changed_by=customer_user,
                notes="Customer approved the ticket.")
    return payment


# ---------------------------------------------------------------------
# 5. Release Payment — SIRF admin, sirf approval ke baad
# ---------------------------------------------------------------------

@transaction.atomic
def release_payment(payment: Payment, released_by_admin, release_notes: str = ""):
    """
    Escrow ka sabse critical function. Teeno checks fail-safe hain:
      1. escrow_status held_in_escrow hona chahiye
      2. booking.customer_approved True hona chahiye
      3. released_by_admin.is_staff True hona chahiye
    """
    if not released_by_admin.is_staff:
        raise PermissionError("Sirf admin payment release kar sakta hai.")

    if payment.escrow_status != PaymentStatus.HELD_IN_ESCROW:
        raise ValueError("Payment escrow mein hold nahi hai, release nahi ho sakta.")

    if not payment.booking.customer_approved:
        raise ValueError("Customer approval se pehle payment release nahi ho sakta.")

    if hasattr(payment, "release_record"):
        raise ValueError("Ye payment pehle hi release ho chuka hai.")

    raast_reference = ""
    if payment.payment_method == "raast":
        # Snapshot — us waqt ke agent ke raast_id ka
        raast_reference = payment.agent_raast_id or ""

    PaymentRelease.objects.create(
        payment=payment,
        released_by=released_by_admin,
        amount_released=payment.amount,
        release_notes=release_notes,
        raast_payout_reference=raast_reference,
    )

    payment.escrow_status = PaymentStatus.RELEASED
    payment.released_at = timezone.now()
    payment.released_by = released_by_admin
    payment.save(update_fields=["escrow_status", "released_at", "released_by", "updated_at"])

    escrow_txn = payment.escrow_transaction
    escrow_txn.status = EscrowTransaction.Status.RELEASED
    escrow_txn.save(update_fields=["status", "updated_at"])

    _set_status(payment, PaymentStatus.RELEASED, changed_by=released_by_admin,
                notes=release_notes or "Payment released by admin.")

    return payment


# ---------------------------------------------------------------------
# 6. Cancel / Refund (branches only allowed before RELEASED)
# ---------------------------------------------------------------------

def cancel_payment(payment: Payment, cancelled_by, reason: str = ""):
    if payment.payment_status == PaymentStatus.RELEASED:
        raise ValueError("Released payment cancel nahi ho sakta.")
    _set_status(payment, PaymentStatus.CANCELLED, changed_by=cancelled_by, notes=reason)
    return payment


def refund_payment(payment: Payment, refunded_by, reason: str = ""):
    if payment.payment_status == PaymentStatus.RELEASED:
        raise ValueError("Released payment refund nahi ho sakta — ye alag dispute process hoga.")
    if not refunded_by.is_staff:
        raise PermissionError("Sirf admin refund process kar sakta hai.")

    if hasattr(payment, "escrow_transaction"):
        escrow_txn = payment.escrow_transaction
        escrow_txn.status = EscrowTransaction.Status.REFUNDED
        escrow_txn.save(update_fields=["status", "updated_at"])

    _set_status(payment, PaymentStatus.REFUNDED, changed_by=refunded_by, notes=reason)
    return payment