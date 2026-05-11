from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.forms import UserCreationForm

User = get_user_model()


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model  = User
        fields = ("username", "email", "role")


# ---------------------------------------------------------------------------
# Profile (Personal tab)
# ---------------------------------------------------------------------------

class ProfileForm(forms.ModelForm):
    """
    Handles the Personal tab of the profile page.
    Add / remove fields to match your User model exactly.
    Fields rendered by Django form: username, email, phone, birth_date,
    city, country, bio.
    first_name / last_name / role are taken raw from POST (no widget needed).
    """

    class Meta:
        model  = User
        fields = [
            "username",
            "email",
            "phone",
            "birth_date",
            "city",
            "country",
            "bio",
        ]
        widgets = {
            "username": forms.TextInput(attrs={
                "class":       "f-input",
                "placeholder": "your_username",
                "autocomplete":"username",
            }),
            "email": forms.EmailInput(attrs={
                "class":       "f-input",
                "placeholder": "email@example.com",
                "autocomplete":"email",
            }),
            "phone": forms.TextInput(attrs={
                "class":       "f-input",
                "placeholder": "+212 6 00 00 00 00",
                "autocomplete":"tel",
            }),
            "birth_date": forms.DateInput(attrs={
                "class": "f-input",
                "type":  "date",
            }),
            "city": forms.TextInput(attrs={
                "class":       "f-input",
                "placeholder": "City",
            }),
            "country": forms.TextInput(attrs={
                "class":       "f-input",
                "placeholder": "Country",
            }),
            "bio": forms.Textarea(attrs={
                "class":       "f-textarea",
                "placeholder": "A few words about yourself...",
                "rows":        3,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Mark non-required fields as optional so partial updates work
        for field_name in ("phone", "birth_date", "city", "country", "bio"):
            self.fields[field_name].required = False


# ---------------------------------------------------------------------------
# Password change (Security tab)
# ---------------------------------------------------------------------------

class PasswordChangeForm(forms.Form):
    """
    Custom password-change form that verifies the current password,
    then validates and sets the new one.
    Uses Django's built-in password validators.
    """

    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class":        "f-input",
            "placeholder":  "Enter current password",
            "autocomplete": "current-password",
        }),
        label="Current password",
    )
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class":        "f-input",
            "placeholder":  "Min. 8 characters",
            "autocomplete": "new-password",
            "oninput":      "checkStrength(this.value)",
        }),
        label="New password",
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class":        "f-input",
            "placeholder":  "Repeat new password",
            "autocomplete": "new-password",
        }),
        label="Confirm new password",
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        current = self.cleaned_data.get("current_password")
        if not self.user.check_password(current):
            raise forms.ValidationError("Your current password is incorrect.")
        return current

    def clean(self):
        cleaned = super().clean()
        pw1 = cleaned.get("new_password1")
        pw2 = cleaned.get("new_password2")
        if pw1 and pw2 and pw1 != pw2:
            raise forms.ValidationError({"new_password2": "The two passwords don't match."})
        if pw1:
            password_validation.validate_password(pw1, self.user)
        return cleaned

    def save(self):
        """Set the new password and return the user."""
        password = self.cleaned_data["new_password1"]
        self.user.set_password(password)
        self.user.save()
        return self.user