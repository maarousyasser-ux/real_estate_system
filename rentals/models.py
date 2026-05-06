from django.db import models
from django.conf import settings
from properties.models import Property

User = settings.AUTH_USER_MODEL


class RentalRequest(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    )

    property = models.ForeignKey(Property, on_delete=models.CASCADE)
    tenant = models.ForeignKey(User, on_delete=models.CASCADE, related_name="rental_requests")

    message = models.TextField(blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tenant} → {self.property}"