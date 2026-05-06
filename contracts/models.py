from django.db import models, transaction
from django.conf import settings
from django.utils import timezone
from dateutil.relativedelta import relativedelta

# Assuming these apps/models exist as per your imports
from properties.models import Property
from tenants.models import Tenant

class Contract(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('pending', 'Pending Signature'),
    ]

    # ───── RELATIONS ─────
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='contracts')
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='contracts')

    agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='agent_contracts',
        limit_choices_to={'role': 'agent'}
    )

    landlord = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='landlord_contracts',
        limit_choices_to={'role': 'landlord'}
    )

    # ───── FINANCIAL ─────
    rent_amount = models.DecimalField(max_digits=10, decimal_places=2)
    deposit = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # ───── DATES ─────
    start_date = models.DateField()
    end_date = models.DateField()
    signed_at = models.DateTimeField(auto_now_add=True)

    # ───── STATUS ─────
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    active = models.BooleanField(default=True)

    # ───── NOTES ─────
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-signed_at']

    def __str__(self):
        return f"{self.property.title} — {self.tenant}"

    # ─────────────────────────────
    # CALCULATIONS
    # ─────────────────────────────
    def days_remaining(self):
        today = timezone.now().date()
        return max(0, (self.end_date - today).days)

    def is_expiring_soon(self):
        return 0 < self.days_remaining() <= 30

    # ─────────────────────────────
    # PAYMENT GENERATION
    # ─────────────────────────────
    def generate_payments(self):
        """
        Generates monthly payment records from start_date to end_date.
        """
        # Local import to avoid circular dependency issues
        from payments.models import Payment

        payments_to_create = []
        current_date = self.start_date

        with transaction.atomic():
            while current_date <= self.end_date:
                month_label = current_date.strftime("%B %Y")

                # Check if a payment for this contract and month already exists
                exists = Payment.objects.filter(
                    contract=self,
                    due_date__year=current_date.year,
                    due_date__month=current_date.month
                ).exists()

                if not exists:
                    payments_to_create.append(
                        Payment(
                            contract=self,
                            amount=self.rent_amount,
                            due_date=current_date,
                            month=month_label,
                            status="pending"
                        )
                    )

                # Move to the same day in the next month
                current_date += relativedelta(months=1)

            # Save everything in one database hit
            if payments_to_create:
                Payment.objects.bulk_create(payments_to_create)
                return len(payments_to_create)
        return 0