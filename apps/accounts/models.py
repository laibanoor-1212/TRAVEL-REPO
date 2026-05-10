from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):

    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('stakeholder', 'Stakeholder'),
        ('user', 'User'),
    )

    role = models.CharField(max_length=20,choices=ROLE_CHOICES,default='user')

    # Stakeholder approval
    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return self.username
