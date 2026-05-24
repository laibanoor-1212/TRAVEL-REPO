from django.db import models
from django.conf import settings

class AgentKYC(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rollback', 'Rollback'),
        ('rejected', 'Rejected'),
    )
    IATA_TYPE_CHOICES = (
        ('own', 'Own IATA'),
        ('reference', 'Reference IATA'),
    )
    user = models.OneToOneField( settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='agent_kyc',null=True, blank=True)
    agency_name = models.CharField(max_length=255)
    owner_name = models.CharField(max_length=255)
    phone_no = models.CharField(max_length=20 )
    whatsapp_no = models.CharField(max_length=20,blank=True)
    office_address = models.TextField()
    is_hajj = models.BooleanField( default=False)
    is_ziyarat = models.BooleanField(default=False)
    ntn_no = models.CharField(max_length=100 )
    dts_no = models.CharField(max_length=100 )
    cnic_no = models.CharField(max_length=30)
    ntn_doc = models.FileField(upload_to='agent_kyc/ntn/')
    dts_doc = models.FileField( upload_to='agent_kyc/dts/' )
    cnic_f = models.FileField( upload_to='agent_kyc/cnic/')
    cnic_b = models.FileField(upload_to='agent_kyc/cnic/')
    munazzam_no = models.CharField( max_length=255,blank=True)
    munazzam_doc = models.FileField(upload_to='agent_kyc/munazzam/',blank=True, null=True)
    iata_type = models.CharField(max_length=20,choices=IATA_TYPE_CHOICES, blank=True)
    iata_no = models.CharField( max_length=255, blank=True)
    iata_doc = models.FileField( upload_to='agent_kyc/iata/',blank=True,null=True)
    # REFERENCE IATA
    ref_agency_name = models.CharField( max_length=255, blank=True)
    iata_ref_doc = models.FileField(upload_to='agent_kyc/iata_reference/', blank=True, null=True )
    ziy_no = models.CharField( max_length=255,blank=True )
    ziy_doc = models.FileField( upload_to='agent_kyc/ziy/',blank=True, null=True)
    bank_iban = models.CharField(max_length=255,   blank=True)
    bank_name = models.CharField(max_length=255, blank=True)
    easypaisa_no = models.CharField( max_length=20, blank=True)
    easypaisa_name = models.CharField(max_length=255,blank=True)
    jazzcash_no = models.CharField( max_length=20,blank=True )
    jazzcash_name = models.CharField( max_length=255,blank=True )
    kyc_status = models.CharField(max_length=20,choices=STATUS_CHOICES, default='pending')
    admin_comment = models.TextField(blank=True)
    submission_count = models.PositiveIntegerField(default=0)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):

        return f"{self.agency_name} - {self.kyc_status}"
    
    