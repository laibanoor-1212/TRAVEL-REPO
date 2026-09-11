from django.db import models
from django.conf import settings
from django.utils.text import slugify
from packages.models import Package
from customers.models import CustomerProfile


class Bookings(models.Model):
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('action_required', 'Action Required'),
        ('visa_processing', 'Visa Processing'),
        ('ticket_issued', 'Ticket Issued'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('rejected', 'Rejected'),
        ('refunded', 'Refunded'),
    ]

    user = models.ForeignKey( settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings')
    package = models.ForeignKey(Package, on_delete=models.CASCADE,related_name='bookings')
    booking_id = models.CharField(max_length=100, unique=True, blank=True)
    slug = models.SlugField(unique=True, blank=True)
    total_persons = models.PositiveIntegerField(default=1)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=30,choices=STATUS_CHOICES,default='pending')
    customer_note = models.TextField(blank=True, null=True)
    admin_note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):

        if not self.booking_id:
            last_id = Bookings.objects.count() + 1
            self.booking_id = f"SEH-BKG-{last_id:05d}"

        if not self.slug:
            self.slug = slugify(self.booking_id)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.booking_id


class BookingCustomers(models.Model):
    VERIFICATION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('incomplete', 'Incomplete'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('resubmitted', 'Resubmitted by User'),
        ('rollback', 'Rollback Requested'),
    ]
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
    ]
    
    booking = models.ForeignKey(Bookings, on_delete=models.CASCADE, related_name='customer_profiles')
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    cnic = models.CharField(max_length=30)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    passport_number = models.CharField(max_length=50, blank=True, null=True)
    passport_issue_date = models.DateField(blank=True, null=True)
    passport_expiry = models.DateField(blank=True, null=True)
    passport_scan = models.FileField(upload_to='booking/passports/', blank=True, null=True)
    digital_photo = models.ImageField(upload_to='booking/photos/', blank=True, null=True)
    cnic_front = models.ImageField(upload_to='booking/cnic/front/', blank=True, null=True)
    cnic_back = models.ImageField(upload_to='booking/cnic/back/', blank=True, null=True)

    verification_status = models.CharField(
        max_length=20, 
        choices=VERIFICATION_STATUS_CHOICES, 
        default='pending'
    )
    field_statuses = models.JSONField(default=dict, blank=True)  
    rollback_remarks = models.JSONField(default=dict, blank=True) 
    rejection_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.booking.booking_id})"

class BookingStatusHistory(models.Model):

    booking = models.ForeignKey(
        Bookings,
        on_delete=models.CASCADE,
        related_name='status_history'
    )

    old_status = models.CharField(max_length=30)
    new_status = models.CharField(max_length=30)

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    remarks = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.booking.booking_id} - {self.new_status}"
class Ticket(models.Model):
    booking = models.OneToOneField(
        Bookings, on_delete=models.CASCADE, related_name='ticket'
    )
    agent = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='uploaded_tickets'
    )
    ticket_file = models.FileField(upload_to='tickets/')
    notes = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    customer_approved = models.BooleanField(default=False)
    customer_approved_at = models.DateTimeField(blank=True, null=True)
    customer_rejection_reason = models.TextField(blank=True, null=True)
    def __str__(self):
        return f"Ticket for Booking #{self.booking_id}"

class BookingDocument(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    FIELD_TYPE_CHOICES = (
        ('file', 'File Upload'),
        ('text', 'Text Information'),
    )

    booking = models.ForeignKey(Bookings, on_delete=models.CASCADE, related_name='documents')
    field_name = models.CharField(max_length=100)
    field_type = models.CharField(max_length=10, choices=FIELD_TYPE_CHOICES, default='file')
    text_value = models.TextField(blank=True, null=True)
    file_value = models.FileField(upload_to='booking_docs/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    rejection_reason = models.TextField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.booking.id} - {self.field_name}"



