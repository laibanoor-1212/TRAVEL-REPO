from django.db import models
from django.contrib.auth import get_user_model
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