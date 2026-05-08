from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    phone = models.CharField(max_length=15, blank=True, null=True)
    birth_date = models.DateField(null=True, blank=True)

    ROLE_CHOICES = (
        ('landlord', 'Landlord'),
        ('agent', 'Agent'),
        ('tenant', 'Tenant'),
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='tenant'
    )

    def __str__(self):
        return self.username