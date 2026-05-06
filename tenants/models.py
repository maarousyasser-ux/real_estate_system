from django.db import models
from django.conf import settings
from properties.models import Property

class Tenant(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    property = models.ForeignKey(Property, on_delete=models.SET_NULL, null=True, related_name='tenants')
    phone_number = models.CharField(max_length=20, default="N/A")
    emergency_contact = models.CharField(max_length=255, null=True, blank=True) 
    lease_start = models.DateField(null=True, blank=True)
    lease_end = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        name = self.user.get_full_name() or self.user.username
        prop = self.property.title if self.property else 'No Property'
        return f"{name} - {prop}"