from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.timezone import now
from django.conf import settings  # User model import karne ke liye

class PackageType(models.Model):
    name = models.CharField(max_length=255)  
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
        
class Package(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('draft', 'Draft'),
        ('closed', 'Closed'),
    ]

    TIER_CHOICES = [
        ('economy', 'Economy'),
        ('standard', 'Standard'),
        ('vip', 'VIP'),
        ('luxury', 'Luxury'),
    ]

   
    agency = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='packages',
        default=1  
    )

    # --- PART 2: PACKAGE SPECIFICATIONS ---
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    package_type = models.ForeignKey(PackageType, on_delete=models.CASCADE)
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default='standard')
    country = models.CharField(max_length=100, default='Saudi Arabia')
    city = models.CharField(max_length=100, default='Makkah')

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=100000,
        validators=[
            MinValueValidator(100000),
            MaxValueValidator(2500000)
        ]
    )

    total_seats = models.PositiveIntegerField(default=50)
    booked_seats = models.PositiveIntegerField(default=0)
    departure_date = models.DateField(default=now)
    application_deadline = models.DateField(default=now)

   
    duration_days = models.PositiveIntegerField(default=15)
    makkah_hotel = models.CharField(max_length=255, default='Standard Hotel')
    madinah_hotel = models.CharField(max_length=255, default='Standard Hotel')
    
    
    visa = models.BooleanField(default=False)
    ticket = models.BooleanField(default=False)
    transport = models.BooleanField(default=False)
    ziyarat = models.BooleanField(default=False)

   
    description = models.TextField(default='Package details coming soon...')
    banner = models.ImageField(upload_to='package_banners/', default='package_banners/default.jpg')

   
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    view_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def seats_left(self):
        return self.total_seats - self.booked_seats

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.agency.stakeholder_profile.agency_name if hasattr(self.agency, 'stakeholder_profile') else self.agency.username})"