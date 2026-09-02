from django.db import models


class ContactMessage(models.Model):
    CATEGORY_CHOICES = [
        ('pilgrim', 'Pilgrim / Traveler'),
        ('agent', 'Travel Agent'),
        ('payment', 'Payment & Escrow'),
        ('general', 'General Inquiry'),
    ]

    name = models.CharField(max_length=150)
    email = models.EmailField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} - {self.category} ({self.created_at.strftime('%Y-%m-%d')})"

