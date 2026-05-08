from django import forms
from .models import MaintenanceRequest, MaintenanceComment


class MaintenanceRequestForm(forms.ModelForm):

    class Meta:
        model = MaintenanceRequest

        # ❌ REMOVE unsafe fields
        fields = [
            'title',
            'category',
            'priority',
            'description',
            'image'
        ]

        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Brief summary of the issue',
            }),

            'category': forms.Select(attrs={
                'class': 'form-select'
            }),

            'priority': forms.Select(attrs={
                'class': 'form-select'
            }),

            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe the issue in detail…',
            }),

            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),
        }


class MaintenanceStatusForm(forms.ModelForm):
    """Staff-only form to update status + internal notes"""

    class Meta:
        model = MaintenanceRequest
        fields = ['status', 'notes']

        widgets = {
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),

            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Internal notes (not visible to tenant)…',
            }),
        }


class MaintenanceCommentForm(forms.ModelForm):

    class Meta:
        model = MaintenanceComment
        fields = ['body', 'is_internal']

        widgets = {
            'body': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Add a comment or update…',
            }),

            'is_internal': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

        labels = {
            'body': 'Comment',
            'is_internal': 'Internal only (hidden from tenant)',
        }