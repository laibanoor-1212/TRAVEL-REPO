from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils.timezone import now
import uuid
class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('welcome', 'Welcome'),
        ('register', 'User Registration'),
        ('login', 'User Login'),
        ('logout', 'User Logout'),
        ('password_reset', 'Password Reset'),
        ('email_verify', 'Email Verification'),
        ('profile_update', 'Profile Updated'),
        ('account_locked', 'Account Locked'),
        ('account_unlocked', 'Account Unlocked'),
        ('kyc_submitted', 'KYC Submitted'),
        ('kyc_pending', 'KYC Pending'),
        ('kyc_approved', 'KYC Approved'),
        ('kyc_rejected', 'KYC Rejected'),
        ('missing_documents', 'Missing Documents'),
        ('document_uploaded', 'Document Uploaded'),
        ('document_expired', 'Document Expired'),
        ('package_created', 'Package Created'),
        ('package_updated', 'Package Updated'),
        ('package_deleted', 'Package Deleted'),
        ('package_approved', 'Package Approved'),
        ('package_rejected', 'Package Rejected'),
        ('package_expired', 'Package Expired'),
        ('package_available', 'Package Available'),
        ('package_full', 'Package Fully Booked'),
        ('booking_created', 'Booking Created'),
        ('booking_pending', 'Booking Pending'),
        ('booking_confirmed', 'Booking Confirmed'),
        ('booking_cancelled', 'Booking Cancelled'),
        ('booking_rejected', 'Booking Rejected'),
        ('booking_completed', 'Booking Completed'),
        ('booking_refunded', 'Booking Refunded'),
        ('traveler_added', 'Traveler Added'),
        ('traveler_updated', 'Traveler Updated'),
        ('passport_expiring', 'Passport Expiring'),
        ('visa_required', 'Visa Required'),
        ('payment_pending', 'Payment Pending'),
        ('payment_received', 'Payment Received'),
        ('payment_verified', 'Payment Verified'),
        ('payment_failed', 'Payment Failed'),
        ('payment_refunded', 'Payment Refunded'),
        ('installment_due', 'Installment Due'),
        ('invoice_generated', 'Invoice Generated'),
        ('visa_submitted', 'Visa Submitted'),
        ('visa_processing', 'Visa Processing'),
        ('visa_approved', 'Visa Approved'),
        ('visa_rejected', 'Visa Rejected'),
        ('flight_added', 'Flight Added'),
        ('flight_updated', 'Flight Updated'),
        ('flight_cancelled', 'Flight Cancelled'),
        ('flight_rescheduled', 'Flight Rescheduled'),
        ('ticket_issued', 'Ticket Issued'),
        ('hotel_confirmed', 'Hotel Confirmed'),
        ('hotel_changed', 'Hotel Changed'),
        ('hotel_cancelled', 'Hotel Cancelled'),
        ('transport_confirmed', 'Transport Confirmed'),
        ('transport_cancelled', 'Transport Cancelled'),
        ('ziyarat_schedule', 'Ziyarat Schedule'),
        ('agent_registered', 'Agent Registered'),
        ('agent_approved', 'Agent Approved'),
        ('agent_rejected', 'Agent Rejected'),
        ('commission_added', 'Commission Added'),
        ('commission_paid', 'Commission Paid'),
        ('support_ticket_created', 'Support Ticket Created'),
        ('support_reply', 'Support Reply'),
        ('support_closed', 'Support Closed'),
        ('departure_reminder', 'Departure Reminder'),
        ('return_reminder', 'Return Reminder'),
        ('payment_reminder', 'Payment Reminder'),
        ('document_reminder', 'Document Reminder'),
        ('offer', 'Special Offer'),
        ('discount', 'Discount'),
        ('new_package', 'New Package'),
        ('announcement', 'Announcement'),
        ('admin_message', 'Admin Message'),
        ('maintenance', 'System Maintenance'),
        ('security_alert', 'Security Alert'),
        ('system', 'System Notification'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    uuid = models.UUIDField(default=uuid.uuid4,editable=False,unique=True)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='notifications')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='sent_notifications')
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=300,unique=True,blank=True)
    message = models.TextField()
    notification_type = models.CharField(max_length=50,choices=NOTIFICATION_TYPES,default='system')
    priority = models.CharField(max_length=10,choices=PRIORITY_CHOICES,default='medium')
    is_read = models.BooleanField(default=False)
    is_seen = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    redirect_url = models.URLField(blank=True,null=True)
    icon = models.CharField(max_length=100,blank=True,null=True,help_text="FontAwesome icon class")
    image = models.ImageField(upload_to='notifications/images/',blank=True,null=True )
    extra_data = models.JSONField( blank=True, null=True)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)
    read_at = models.DateTimeField(blank=True,null=True)
    expires_at = models.DateTimeField(blank=True,null=True)
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def save(self, *args, **kwargs):

        if not self.slug:
            self.slug = slugify(
                f"{self.recipient.id}-{self.notification_type}-{uuid.uuid4().hex[:6]}"
            )

        super().save(*args, **kwargs)

   

    def __str__(self):
        return f"{self.recipient} - {self.title}"
