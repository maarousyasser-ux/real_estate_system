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

        # ✅ IMPORTANT: force correct HTML date inputs
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # deposit optional
        self.fields["deposit"].required = False

        # better UX defaults
        self.fields["deposit"].initial = 0