from django.db import models
from django.contrib.auth import get_user_model
from django_ckeditor_5.fields import CKEditor5Field
User = get_user_model()

class Complaint(models.Model):
    COMPLAINT_TYPES = [
    
        ('no_ticket', 'Flight Ticket Not Received Yet (Customer Issue)'),
        ('visa_delay', 'Visa Processing Delay / Document Issue'),
        ('passport_issue', 'Passport Return / Courier Handling Issue'),
        ('no_payment', 'Payment Pending / Not Received (Agent Issue)'),
        ('wrong_billing', 'Incorrect Amount Charged / Double Payment'),
        ('refund_issue', 'Refund Request Pending / Cash Back Delay'),
        ('transport_missing', 'Transport/Bus Not Arrived at Airport or Hotel'),
        ('driver_behavior', 'Driver Misbehavior / Route Mismanagement'),
        ('luggage_lost', 'Luggage Lost / Handling Issue during Transport'),
        ('hotel_not_booked', 'Hotel Booking Not Found at Check-in (Voucher Issue)'),
        ('room_quality', 'Room Quality/Amenities Not as Promised (Distance/Food/AC)'),
        ('ziarat_issue', 'Makkah/Madinah Ziarat Tour Skipped or Delayed'),
        ('info_not_sent', 'My Information/Data Not Forwarded to Supplier'),
        ('portal_error', 'Web App Technical Error / System Crash'),
        ('other', 'Other Operational Issues / Emergency Assistance'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('in_progress', 'Under Investigation'),
        ('resolved', 'Resolved / Closed'),
    ]

    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('agent', 'Agent'),
    ]
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='complaints',
        verbose_name="Filer / Complainant"
    )
    user_role = models.CharField(
        max_length=20, 
        choices=ROLE_CHOICES,
        verbose_name="Role Type"
    )
    complaint_type = models.CharField(
        max_length=30, 
        choices=COMPLAINT_TYPES,
        verbose_name="Issue Category"
    )
    
    subject = models.CharField(
        max_length=255,
        verbose_name="Subject Title"
    )
    description = models.TextField(
        verbose_name="Detailed Grievance"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Filed Date & Time"
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        verbose_name="Action Status"
    )

    class Meta:
        verbose_name = "Customer & Agent Complaint"
        verbose_name_plural = "Complaints Control Center"
        ordering = ['-created_at'] 

    def __str__(self):
        return f"#{self.id} | {self.user.email} - {self.get_complaint_type_display()}"



class SystemSetting(models.Model):
    primary_currency = models.CharField(max_length=10, default="PKR", choices=[('PKR', 'PKR'), ('SAR', 'SAR'), ('USD', 'USD')])
    timezone = models.CharField(max_length=50, default="Asia/Karachi")
    maintenance_mode = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        self.pk = 1  
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Safar-e-Haram Platform Settings"


class GuidePage(models.Model):
    # Unique slug identifying each route (e.g., 'miqat', 'tawaf', 'mashad', 'karbala')
    page_slug = models.SlugField(max_length=100, unique=True, help_text="Page key identifier matching view route")
    title = models.CharField(max_length=200, help_text="Page Heading Title")
    banner_image = models.ImageField(upload_to='guides/banners/', blank=True, null=True)
    content = CKEditor5Field('Guide Content', config_name='extends', blank=True)
    is_published = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.page_slug})"