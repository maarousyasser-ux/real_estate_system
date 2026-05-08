from django import forms
from .models import Contract


class ContractForm(forms.ModelForm):

    class Meta:
        model = Contract
        fields = [
            "rent_amount",
            "deposit",
            "start_date",
            "end_date",
            "notes",
        ]

        widgets = {
            "rent_amount": forms.NumberInput(attrs={
                "min": 0,
                "step": "0.01",
                "placeholder": "Monthly rent"
            }),

            "deposit": forms.NumberInput(attrs={
                "min": 0,
                "step": "0.01",
                "placeholder": "Security deposit"
            }),

            "start_date": forms.DateInput(attrs={
                "type": "date"
            }),

            "end_date": forms.DateInput(attrs={
                "type": "date"
            }),

            "notes": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Optional notes..."
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["deposit"].required = False
        self.fields["deposit"].initial = 0

    # 🔥 VALIDATION (IMPORTANT FIX)
    def clean(self):
        cleaned_data = super().clean()

        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        rent = cleaned_data.get("rent_amount")
        deposit = cleaned_data.get("deposit")

        # date logic
        if start_date and end_date and end_date <= start_date:
            raise forms.ValidationError(
                "End date must be after start date."
            )

        # prevent negative values
        if rent is not None and rent < 0:
            self.add_error("rent_amount", "Rent cannot be negative.")

        if deposit is not None and deposit < 0:
            self.add_error("deposit", "Deposit cannot be negative.")

        return cleaned_data