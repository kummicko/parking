from django import forms
from .models import ParkingUser, ParkingSpot, ParkingConfig


class ParkingUserForm(forms.ModelForm):
    class Meta:
        model = ParkingUser
        fields = ["first_name", "last_name", "phone", "email", "plate", "notes"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 2}),
        }


class ParkingSpotForm(forms.ModelForm):
    class Meta:
        model = ParkingSpot
        fields = ["number", "is_active", "notes"]
        widgets = {
            "number": forms.TextInput(attrs={"class": "form-input"}),
            "notes": forms.Textarea(attrs={"class": "form-input", "rows": 3}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }


class ParkingConfigForm(forms.ModelForm):
    class Meta:
        model = ParkingConfig
        fields = ["monthly_price"]
        widgets = {
            "monthly_price": forms.NumberInput(
                attrs={
                    "class": "form-input",
                    "step": "100",
                    "autofocus": True,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["monthly_price"].label = "Mesečna cena pretplate"
        self.fields["monthly_price"].required = True
