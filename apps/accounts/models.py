import re
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.core.exceptions import ValidationError
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
  groups = models.ManyToManyField(
      Group, related_name='custom_user_groups', blank=True
  )
  user_permissions = models.ManyToManyField(
      Permission, related_name='custom_user_permissions', blank=True
  )
  date_joined = models.DateTimeField(default=timezone.now)

  def clean(self):
    super().clean()
    if self.phone_number:
      digits_only = re.sub(r'\D', '', self.phone_number)
      if len(digits_only) < 11 or len(digits_only) > 13:
        raise ValidationError({
            'phone_number': (
                'Phone number must be between 11 and 13 digits long.'
            )
        })
    if self.role == 'stakeholder':
      if not self.agency_name or not self.agency_name.strip():
        raise ValidationError(
            {'agency_name': 'Agency name is required for stakeholders.'}
        )

      clean_agency = self.agency_name.strip()
      letters_only = re.sub(r'[^a-zA-Z]', '', clean_agency)
      if len(letters_only) < 3:
        raise ValidationError(
            {'agency_name': 'Agency name must contain at least 3 letters.'}
        )
      valid_agency_regex = r"^[a-zA-Z0-9\s.&'-]+$"
      if not re.match(valid_agency_regex, clean_agency):
        raise ValidationError({
            'agency_name': (
                'Agency name can only contain letters, numbers, spaces, and'
                " standard characters like &, -, ., '"
            )
        })

  def save(self, *args, **kwargs):
    if self.is_superuser:
      self.role = 'admin'
      self.is_approved = True
      self.is_staff = True
    elif self.role == 'admin':
      self.is_staff = True

    super().save(*args, **kwargs)

  @property
  def is_stakeholder(self):
    return self.role and self.role.lower() in ['stakeholder', 'agent']

  def __str__(self):
    return self.username