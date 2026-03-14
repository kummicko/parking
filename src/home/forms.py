from django import forms
from .models import ParkingUser


class ParkingUserForm(forms.ModelForm):
    class Meta:
        model = ParkingUser
        fields = ["first_name", "last_name", "phone", "email", "plate", "notes"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 2}),
        }
