from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.timezone import now
from datetime import date
from django.conf import settings

class PackageType(models.Model):
    name = models.CharField(max_length=255)  
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    image = models.ImageField(upload_to='package_types/', blank=True, null=True)

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
        ('blocked', 'Blocked'),
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
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    package_type = models.ForeignKey(PackageType, on_delete=models.CASCADE)
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default='standard')
    country = models.CharField(max_length=100, default='Saudi Arabia')
    city = models.CharField(max_length=100, blank=True, null=True, default='Makkah')

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
    makkah_hotel = models.CharField(max_length=255, blank=True, null=True)
    madinah_hotel = models.CharField(max_length=255, blank=True, null=True)
    visa = models.BooleanField(default=False)
    ticket = models.BooleanField(default=False)
    transport = models.BooleanField(default=False)
    ziyarat = models.BooleanField(default=False)
    meals = models.BooleanField(default=False) 

    description = models.TextField(default='Package details coming soon...')
    banner = models.ImageField(upload_to='package_banners/', default='package_banners/default.jpg')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    view_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def seats_left(self):
        return max(0, self.total_seats - self.booked_seats)

    @property
    def is_available(self):
        today = date.today()
        has_seats = self.seats_left() > 0
        not_expired = self.application_deadline >= today
        return self.status == 'active' and has_seats and not_expired

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        orig_slug = self.slug
        counter = 1
        while Package.objects.filter(slug=self.slug).exclude(id=self.id).exists():
            self.slug = f"{orig_slug}-{counter}"
            counter += 1

        if self.seats_left() <= 0:
            self.status = 'closed'

        super().save(*args, **kwargs)

    def __str__(self):
        agency_name = self.agency.stakeholder_profile.agency_name if hasattr(self.agency, 'stakeholder_profile') else self.agency.username
        return f"{self.name} ({agency_name})"