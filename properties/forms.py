from django import forms
from django.contrib.auth import get_user_model
from .models import Property

User = get_user_model()


class PropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = [
            'title', 'owner', 'property_type', 'status',
            'price', 'monthly_rent', 'size', 'units_count',
            'address', 'image'
        ]

        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g. Oasis Villa'}),
            'address': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Full Address in Casablanca...'
            }),
            'price': forms.NumberInput(attrs={'placeholder': 'Total Value'}),
            'monthly_rent': forms.NumberInput(attrs={'placeholder': 'Rent per Month'}),
            'size': forms.NumberInput(attrs={'placeholder': 'm²'}),
            'units_count': forms.NumberInput(attrs={'placeholder': 'Number of units'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # ========================
        # GLOBAL STYLING
        # ========================
        for field in self.fields.values():
            existing_classes = field.widget.attrs.get('class', '')
            field.widget.attrs.update({
                'class': f'{existing_classes} custom-input'.strip()
            })

        # ========================
        # ROLE-BASED LOGIC
        # ========================
        if user:
            # Landlord → auto owner
            if user.role == 'landlord':
                self.fields.pop('owner', None)

            # Agent → must choose landlord
            elif user.role == 'agent':
                self.fields['owner'].queryset = User.objects.filter(role='landlord')
                self.fields['owner'].label = "Property Owner (Landlord)"
                self.fields['owner'].empty_label = "Choose a Landlord"