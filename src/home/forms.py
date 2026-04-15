from django import forms
from .models import ParkingUser, ParkingSpot, ParkingConfig, Payment, Subscription


class ParkingUserForm(forms.ModelForm):
    class Meta:
        model = ParkingUser
        fields = ["first_name", "last_name", "phone", "email", "plate", "notes"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 2}),
        }


class SubscriptionForm(forms.ModelForm):
    start_date = forms.DateField(
        input_formats=["%d.%m.%Y", "%Y-%m-%d"],
        widget=forms.DateInput(
            attrs={"type": "text", "class": "form-input datepicker"},
            format="%d.%m.%Y",
        ),
    )
    end_date = forms.DateField(
        input_formats=["%d.%m.%Y", "%Y-%m-%d"],
        widget=forms.DateInput(
            attrs={"type": "text", "class": "form-input datepicker"},
            format="%d.%m.%Y",
        ),
        required=False,
    )

    class Meta:
        model = Subscription
        fields = ["spot", "start_date", "end_date", "monthly_price"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        config = ParkingConfig.get()
        default_price = config.monthly_price if config else None
        self.fields["monthly_price"].initial = default_price
        self.fields["monthly_price"].required = False
        self.fields["monthly_price"].help_text = "Ostavite prazno za podrazumevanu cenu"
        self.fields["monthly_price"].widget.attrs.update(
            {"class": "form-input", "step": "100", "min": "0"}
        )
        self.fields["end_date"].help_text = "Ostavite prazno za automatsko obnavljanje"
        self.fields["spot"].queryset = ParkingSpot.objects.filter(
            is_active=True
        ).order_by("number")
        self.fields["spot"].widget.attrs.update({"class": "form-input"})


class PaymentForm(forms.ModelForm):
    paid_date = forms.DateField(
        input_formats=["%d.%m.%Y", "%Y-%m-%d"],
        widget=forms.DateInput(
            attrs={"type": "text", "class": "form-input datepicker", "placeholder": "dd.mm.gggg"},
            format="%d.%m.%Y",
        ),
    )

    class Meta:
        model = Payment
        fields = ["amount", "paid_date", "method", "note"]
        widgets = {
            "amount": forms.NumberInput(
                attrs={"class": "form-input", "step": "0.01", "min": "0"}
            ),
            "method": forms.Select(attrs={"class": "form-input"}),
            "note": forms.Textarea(
                attrs={"rows": 2, "class": "form-input resize-none"}
            ),
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
