from django import forms
from .models import ParkingUser, ParkingSpot


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
