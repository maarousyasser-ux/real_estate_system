from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):

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

    phone = models.CharField(
        max_length=15,
        blank=True,
        null=True
    )

    birth_date = models.DateField(
        blank=True,
        null=True
    )

    city = models.CharField(
        max_length=100,
        blank=True
    )

    country = models.CharField(
        max_length=100,
        blank=True
    )

    bio = models.TextField(
        blank=True
    )

    def __str__(self):
        return self.username