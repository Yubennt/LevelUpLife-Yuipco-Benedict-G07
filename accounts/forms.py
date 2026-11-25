from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .validators import time_zone_names

User = get_user_model()


class RegisterForm(UserCreationForm):
    """Register with email + password. New accounts are always regular users (is_staff = False)."""

    class Meta:
        model = User
        fields = ("email", "display_name")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        self.fields["display_name"].required = True
        self.fields["display_name"].help_text = "The name shown in the app (max 50 characters)."
        self.fields["password2"].label = "Confirm password"
        self.fields["password2"].help_text = "Enter the same password again."

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")  # BR-01
        return email


class LoginForm(AuthenticationForm):
    # The field keeps the name "username" because Django and django-axes both look for it.
    username = forms.CharField(label="Email", widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email"}))
    error_messages = {
        "invalid_login": "Incorrect email or password. Please try again.",
        "inactive": "This account is deactivated.",
    }


class ProfileForm(forms.ModelForm):
    """F-02: display name, personal goal, time zone and reminder preference."""

    time_zone = forms.ChoiceField(choices=lambda: [(z, z) for z in time_zone_names()])

    class Meta:
        model = User
        fields = ("display_name", "personal_goal", "time_zone", "reminders_enabled")
        labels = {"reminders_enabled": "Send me habit reminders", "personal_goal": "Personal goal"}
        widgets = {"personal_goal": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["display_name"].required = True
        self.fields["time_zone"].help_text = "Decides when your day and week start for habits and reminders."
        self.fields["personal_goal"].help_text = "What are you levelling up for?"
