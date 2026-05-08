from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class MaintenanceRequest(models.Model):

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]

    CATEGORY_CHOICES = [
        ('plumbing', 'Plumbing'),
        ('electrical', 'Electrical'),
        ('hvac', 'HVAC'),
        ('appliance', 'Appliance'),
        ('structural', 'Structural'),
        ('pest', 'Pest Control'),
        ('cleaning', 'Cleaning'),
        ('other', 'Other'),
    ]

    # =====================================================
    # RELATIONS (FIXED)
    # =====================================================

    tenant = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='maintenance_requests',
        null=True,
        blank=True
    )

    # 🔥 NEW IMPORTANT FIELD
    contract = models.ForeignKey(
        'contracts.Contract',
        on_delete=models.CASCADE,
        related_name='maintenance_requests',
        null=True,
        blank=True
    )

    # =====================================================
    # CORE FIELDS
    # =====================================================

    title = models.CharField(max_length=200)
    description = models.TextField()

    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default='other'
    )

    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    # =====================================================
    # MEDIA
    # =====================================================

    image = models.ImageField(
        upload_to='maintenance/',
        blank=True,
        null=True
    )

    # =====================================================
    # INTERNAL NOTES
    # =====================================================

    notes = models.TextField(
        blank=True,
        help_text="Internal staff notes"
    )

    # =====================================================
    # TIMESTAMPS
    # =====================================================

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    resolved_at = models.DateTimeField(null=True, blank=True)

    # =====================================================
    # META
    # =====================================================

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Maintenance Request'
        verbose_name_plural = 'Maintenance Requests'

    def __str__(self):
        return f"#{self.pk} - {self.title} ({self.get_status_display()})"

    # =====================================================
    # SAVE LOGIC
    # =====================================================

    def save(self, *args, **kwargs):

        if self.status == 'resolved' and not self.resolved_at:
            self.resolved_at = timezone.now()

        elif self.status != 'resolved':
            self.resolved_at = None

        super().save(*args, **kwargs)

    # =====================================================
    # UI HELPERS
    # =====================================================

    @property
    def priority_color(self):
        return {
            'low': 'green',
            'medium': 'blue',
            'high': 'orange',
            'urgent': 'red',
        }.get(self.priority, 'gray')

    @property
    def status_color(self):
        return {
            'pending': 'yellow',
            'in_progress': 'blue',
            'resolved': 'green',
            'closed': 'gray',
        }.get(self.status, 'gray')


# =========================================================
# COMMENTS
# =========================================================

class MaintenanceComment(models.Model):

    request = models.ForeignKey(
        MaintenanceRequest,
        on_delete=models.CASCADE,
        related_name='comments'
    )

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    body = models.TextField()

    is_internal = models.BooleanField(
        default=False,
        help_text="Only visible to staff"
    )

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author} on Request #{self.request_id}"