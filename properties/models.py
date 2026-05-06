from django.db import models
from django.conf import settings

class Property(models.Model):
    STATUS_CHOICES = [('available', 'Available'), ('occupied', 'Occupied'), ('maintenance', 'Maintenance')]
    TYPE_CHOICES = [('apartment', 'Apartment'), ('house', 'House'), ('commercial', 'Commercial'), ('office', 'Office')]

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owned_properties')
    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_properties')
    
    title = models.CharField(max_length=200)
    address = models.TextField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    monthly_rent = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    size = models.PositiveIntegerField(null=True, blank=True)
    units_count = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    property_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='apartment')
    image = models.ImageField(upload_to='properties/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
  
    is_confirmed = models.BooleanField(default=False)

    def __str__(self):
        return self.title
    
    
    
   
@property
def annual_yield(self):
    if self.price and self.monthly_rent:
  
        yield_percent = (self.monthly_rent * 12) / self.price * 100
        return round(yield_percent, 2)
    return 0