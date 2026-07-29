from django.db import models
from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator

class PaymentMethod(models.TextChoices):
    STRIPE = "stripe", "Stripe (Test Mode)"
    RAAST = "raast", "Raast"
   


class PaymentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PAYMENT_SUBMITTED = "payment_submitted", "Payment Submitted"
    PAYMENT_VERIFIED = "payment_verified", "Payment Verified"
    HELD_IN_ESCROW = "held_in_escrow", "Held in Escrow"
    TICKET_UPLOADED = "ticket_uploaded", "Ticket Uploaded"
    CUSTOMER_APPROVED = "customer_approved", "Customer Approved"
    RELEASED = "released", "Released"
    CANCELLED = "cancelled", "Cancelled"
    REFUNDED = "refunded", "Refunded"



class Payment(models.Model):
    booking = models.OneToOneField(
        "bookings.Bookings", on_delete=models.CASCADE, related_name="payment"
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payments_made"
    )
    agent = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payments_received"
    )

    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=10, default="PKR")

   
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True)

    payment_status = models.CharField(
        max_length=30, choices=PaymentStatus.choices, default=PaymentStatus.PENDING
    )
    escrow_status = models.CharField(
        max_length=30, choices=PaymentStatus.choices, default=PaymentStatus.PENDING
    )

    paid_at = models.DateTimeField(blank=True, null=True)
    released_at = models.DateTimeField(blank=True, null=True)
    released_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True,
        related_name="payments_released_by_admin", limit_choices_to={"is_staff": True},
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment #{self.pk} — {self.amount} {self.currency} ({self.get_payment_method_display()})"

    @property
    def agent_raast_id(self):
        """AgentKYC.raast_id tak shortcut — release ke waqt use hoga."""
        agent_kyc = getattr(self.agent, "agent_kyc", None)
        return getattr(agent_kyc, "raast_id", None) if agent_kyc else None



class PaymentProof(models.Model):
  
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="proofs")

    screenshot = models.ImageField(upload_to="payment_proofs/", blank=True, null=True)
    transaction_reference = models.CharField(max_length=255, help_text="Bank/JazzCash transaction ID")

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="uploaded_payment_proofs"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True,
        related_name="verified_payment_proofs", limit_choices_to={"is_staff": True},
    )
    verified_at = models.DateTimeField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True)

    def __str__(self):
        return f"Proof for Payment #{self.payment_id} ({'verified' if self.is_verified else 'pending'})"




class EscrowTransaction(models.Model):
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name="escrow_transaction")
    held_amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Status(models.TextChoices):
        HELD = "held", "Held"
        RELEASED = "released", "Released"
        REFUNDED = "refunded", "Refunded"

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.HELD)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Escrow for Payment #{self.payment_id} — {self.status}"



class PaymentRelease(models.Model):
   
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name="release_record")

    released_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="release_actions",
        limit_choices_to={"is_staff": True},
    )
    amount_released = models.DecimalField(max_digits=12, decimal_places=2)
    release_notes = models.TextField(blank=True)

    
    raast_payout_reference = models.CharField(max_length=255, blank=True)

    released_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Release for Payment #{self.payment_id} by {self.released_by}"




class PaymentStatusLog(models.Model):
  
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="status_logs")

    old_status = models.CharField(max_length=30, choices=PaymentStatus.choices, blank=True, null=True)
    new_status = models.CharField(max_length=30, choices=PaymentStatus.choices)

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True,
        related_name="payment_status_changes",
    )
    notes = models.TextField(blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["changed_at"]

    def __str__(self):
        return f"Payment #{self.payment_id}: {self.old_status} -> {self.new_status}"