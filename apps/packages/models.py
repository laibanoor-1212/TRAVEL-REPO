from django.db import models
from django.utils.text import slugify


class PackageType(models.Model):
    name = models.CharField(max_length=255)  
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

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
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    package_type = models.ForeignKey(PackageType, on_delete=models.CASCADE)
    tier = models.CharField(max_length=20, choices=TIER_CHOICES)
    country = models.CharField(max_length=100)  # Saudi, Iraq, Iran
    city = models.CharField(max_length=100, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_days = models.PositiveIntegerField()
    total_seats = models.PositiveIntegerField()
    booked_seats = models.PositiveIntegerField(default=0)
    application_deadline = models.DateField()
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    view_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def seats_left(self):
        return self.total_seats - self.booked_seats

    def __str__(self):
        return self.name
