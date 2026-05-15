from django.contrib.auth.models import AbstractUser,Group, Permission
from django.db import models
from django.utils import timezone

class CustomUser(AbstractUser):

    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('stakeholder', 'Stakeholder'),
        ('user', 'User'),
    )
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    is_approved = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    agency_name = models.CharField(max_length=255, blank=True, null=True)
    groups = models.ManyToManyField(Group, related_name="custom_user_groups", blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name="custom_user_permissions", blank=True)
    date_joined = models.DateTimeField(default=timezone.now)
   
    class Meta:
        app_label='accounts'

    def __str__(self):
        return self.username
    
