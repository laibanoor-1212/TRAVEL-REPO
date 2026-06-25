from django.db import models
from django.conf import settings
from django.utils.text import slugify
from packages.models import Package# Aapka Booking model
from customers.models import CustomerProfile


class Bookings(models.Model):

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
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

    booking = models.ForeignKey(Bookings,on_delete=models.CASCADE,related_name='CustomerProfile')
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    cnic = models.CharField(max_length=30)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    passport_number = models.CharField( max_length=50,blank=True,null=True)

    passport_expiry = models.DateField(blank=True, null=True)

    # Documents
    passport_scan = models.FileField(upload_to='booking/passports/',blank=True,null=True)
    passport_photo = models.ImageField( upload_to='booking/photos/',blank=True,null=True)

    cnic_front = models.ImageField(upload_to='booking/cnic/front/',blank=True,null=True)
    cnic_back = models.ImageField(upload_to='booking/cnic/back/', blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name


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
