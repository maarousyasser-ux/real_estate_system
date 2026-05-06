from django.db import models
from django.utils import timezone


class Payment(models.Model):
    STATUS_CHOICES = [
        ('paid',    'Paid'),
        ('pending', 'Pending'),
        ('overdue', 'Overdue'),
    ]

    contract   = models.ForeignKey(
        'contracts.Contract',
        on_delete=models.CASCADE,
        related_name='payments'
    )
    amount     = models.DecimalField(max_digits=10, decimal_places=2)
    due_date   = models.DateField()
    paid_date  = models.DateField(null=True, blank=True)
    status     = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    month      = models.CharField(max_length=20)  # e.g. "April 2026"
    notes      = models.TextField(blank=True)

    class Meta:
        ordering = ['-due_date']

    def __str__(self):
        return f"{self.contract.tenant} — {self.month} — {self.get_status_display()}"

    def mark_overdue(self):
        """Call this in a management command or cron to auto-mark overdue payments."""
        if self.status == 'pending' and self.due_date < timezone.now().date():
            self.status = 'overdue'
            self.save(update_fields=['status'])
            
            
            
            
            
            

def update_overdue_payments():
    today = timezone.now().date()

    Payment.objects.filter(
        status="pending",
        due_date__lt=today
    ).update(status="overdue")