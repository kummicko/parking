from django.contrib.auth.forms import AuthenticationForm
from django import forms

# Common Tailwind classes for text/number inputs
TEXT_INPUT_CLASSES = "w-full px-4 py-2 italic border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"


class LoginForm(AuthenticationForm):
    """
    Custom login form based on Django's built-in AuthenticationForm
    with Tailwind CSS styling applied to widgets.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Apply custom widgets and styling
        self.fields["username"].widget = forms.TextInput(
            attrs={"class": TEXT_INPUT_CLASSES, "placeholder": "Unesite korisničko ime"}
        )

        self.fields["password"].widget = forms.PasswordInput(
            attrs={
                "class": TEXT_INPUT_CLASSES,
                "placeholder": "Unesite lozinku",  # Added placeholder for clarity
            }
        )
