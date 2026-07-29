from django.db import models
from django.conf import settings


class CustomerProfile(models.Model):

    GENDER_CHOICES = (
        ('male', 'Male'),
        ('female', 'Female'),
    )

    MARITAL_STATUS_CHOICES = (
        ('single', 'Single'),
        ('married', 'Married'),
    )

    BUDGET_CHOICES = (
        ('economy', 'Economy'),
        ('standard', 'Standard'),
        ('premium', 'Premium'),
        ('luxury', 'Luxury'),
    )

    TRAVEL_TYPE_CHOICES = (
        ('solo', 'Solo'),
        ('family', 'Family'),
        ('group', 'Group'),
    )

    PACKAGE_CHOICES = (
        ('umrah', 'Umrah'),
        ('hajj', 'Hajj'),
        ('iran_iraq', 'Iran / Iraq Ziyarat'),
       
    )
    user = models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='customer_profile' )
    full_name = models.CharField(max_length=255)
    father_name = models.CharField(max_length=255)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField( max_length=20,choices=GENDER_CHOICES)
    marital_status = models.CharField(max_length=20,choices=MARITAL_STATUS_CHOICES,blank=True,null=True)
    phone = models.CharField(max_length=20)
    alternate_phone = models.CharField(max_length=20,blank=True,null=True)
    country = models.CharField(max_length=100,default='Pakistan')
    province = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    address = models.TextField()
    cnic_number = models.CharField(max_length=20,unique=True)
    cnic_front = models.ImageField(upload_to='customer_profile/cnic/')
    cnic_back = models.ImageField(upload_to='customer_profile/cnic/')
    profile_picture = models.ImageField(upload_to='customer_profile/profile/',blank=True,null=True)
    emergency_contact_name = models.CharField(max_length=255,blank=True,null=True)
    relation = models.CharField(max_length=100,blank=True,null=True )
    emergency_contact_phone = models.CharField(max_length=20,blank=True,null=True)
    interested_packages = models.CharField(max_length=255,blank=True,null=True)
    budget_preference = models.CharField(max_length=20,choices=BUDGET_CHOICES,blank=True,null=True)
    travel_type = models.CharField(max_length=20,choices=TRAVEL_TYPE_CHOICES, blank=True,null=True )
    blood_group = models.CharField( max_length=10,blank=True, null=True)
    wheelchair_required = models.BooleanField(default=False)
    medical_condition = models.TextField(blank=True,null=True)
    is_profile_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField( auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name