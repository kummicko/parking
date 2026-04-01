from django.core.exceptions import ValidationError
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone


class ParkingConfig(models.Model):
    monthly_price = models.DecimalField(
        max_digits=8, decimal_places=2, verbose_name="Mesečna cena"
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Datum izmene")

    def save(self, *args, **kwargs):
        self.pk = 1  # singleton — samo jedan red u bazi
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj = cls.objects.filter(pk=1).first()
        if obj is None:
            raise ValueError(
                "Mesečna cena nije podešena. Molimo unesite je u Podešavanjima parkinga."
            )
        return obj

    def __str__(self):
        return f"Mesečna cena: {self.monthly_price}"

    class Meta:
        verbose_name = "Podešavanja parkinga"
        verbose_name_plural = "Podešavanja parkinga"


class ParkingUser(models.Model):
    first_name = models.CharField(max_length=50, verbose_name="Ime")
    last_name = models.CharField(max_length=50, verbose_name="Prezime")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Telefon")
    email = models.EmailField(blank=True, verbose_name="Email")
    plate = models.CharField(
        max_length=20, blank=True, verbose_name="Registarska oznaka"
    )
    notes = models.TextField(blank=True, verbose_name="Napomena")
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Datum registracije"
    )

    def active_subscriptions(self):
        """Sve aktivne pretplate korisnika (može ih biti više)."""
        today = timezone.now().date()
        return self.subscriptions.filter(
            start_date__lte=today,
        ).filter(models.Q(auto_renew=True) | models.Q(end_date__gte=today))

    def total_debt(self):
        """Ukupan dug korisnika po svim aktivnim pretplatama."""
        return sum(s.debt() for s in self.subscriptions.all())

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        verbose_name = "Korisnik parkinga"
        verbose_name_plural = "Korisnici parkinga"
        ordering = ["last_name", "first_name"]


class ParkingSpot(models.Model):
    number = models.CharField(max_length=20, unique=True, verbose_name="Broj mesta")
    is_active = models.BooleanField(default=True, verbose_name="Aktivno")
    notes = models.TextField(blank=True, verbose_name="Napomena")

    def is_available(self):
        return not any(sub.is_active for sub in self.subscriptions.all())

    @property
    def active_subscription(self):
        for sub in self.subscriptions.all():
            if sub.is_active:
                return sub
        return None

    @property
    def active_user(self):
        sub = self.active_subscription
        return sub.user if sub else None

    def __str__(self):
        return f"Mesto {self.number}"

    class Meta:
        verbose_name = "Parking mesto"
        verbose_name_plural = "Parking mesta"
        ordering = ["number"]


class Subscription(models.Model):
    user = models.ForeignKey(
        "ParkingUser",
        on_delete=models.CASCADE,
        related_name="subscriptions",
        verbose_name="Korisnik",
    )

    spot = models.ForeignKey(
        "ParkingSpot",
        on_delete=models.CASCADE,
        related_name="subscriptions",
        verbose_name="Parking mesto",
    )

    start_date = models.DateField(verbose_name="Datum početka")

    end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Datum isteka",
        help_text="Ostavite prazno za automatsko obnavljanje",
    )

    auto_renew = models.BooleanField(
        default=True,
        verbose_name="Automatsko obnavljanje",
    )

    monthly_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Mesečna cena",
        help_text="Ostavite prazno za podrazumevanu cenu",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Datum kreiranja",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Datum izmene",
    )

    # -----------------------
    # Save
    # -----------------------

    def save(self, *args, **kwargs):
        from .models import ParkingConfig

        if not self.monthly_price:
            self.monthly_price = ParkingConfig.get().monthly_price

        super().save(*args, **kwargs)

    # -----------------------
    # Derived Status
    # -----------------------

    @property
    def is_pending(self):
        return self.start_date > timezone.now().date()

    @property
    def is_expired(self):
        if self.auto_renew:
            return False
        return self.end_date and self.end_date < timezone.now().date()

    @property
    def is_active(self):
        today = timezone.now().date()

        if self.start_date > today:
            return False

        if self.is_expired:
            return False

        return True

    @property
    def is_cancelled(self):
        return not self.auto_renew and self.end_date is not None

    # -----------------------
    # Business Logic
    # -----------------------

    def cancel(self):
        """Otkaži pretplatu — neće se obnavljati."""
        self.auto_renew = False
        self.end_date = timezone.now().date()
        self.save()

    # -----------------------
    # Validation
    # -----------------------

    def clean(self):
        """Only one active subscription per spot."""
        if not self.is_active:
            return

        overlapping = Subscription.objects.filter(spot=self.spot).exclude(pk=self.pk)

        for sub in overlapping:
            if sub.is_active:
                raise ValidationError("Ovo parking mesto već ima aktivnu pretplatu.")

    # -----------------------
    # Billing
    # -----------------------

    def is_active_for_month(self, year, month):
        from datetime import date

        month_start = date(year, month, 1)

        if self.start_date > month_start:
            return False

        if self.is_expired:
            return False

        return True

    def total_charged(self):
        import calendar
        from decimal import Decimal

        today = timezone.now().date()
        end = today if self.auto_renew else (self.end_date or today)
        end = min(end, today)
        start = self.start_date

        if end < start:
            return Decimal("0")

        price = self.monthly_price
        total = Decimal("0")

        # same month
        if start.year == end.year and start.month == end.month:
            days_in_month = calendar.monthrange(start.year, start.month)[1]
            days_used = (end - start).days + 1
            total += price * Decimal(days_used) / Decimal(days_in_month)
            return total.quantize(Decimal("0.01"))

        # first month
        days_in_first = calendar.monthrange(start.year, start.month)[1]
        days_used_first = days_in_first - start.day + 1
        total += price * Decimal(days_used_first) / Decimal(days_in_first)

        # last month
        days_in_last = calendar.monthrange(end.year, end.month)[1]
        total += price * Decimal(end.day) / Decimal(days_in_last)

        # full months
        cursor_year, cursor_month = start.year, start.month + 1
        if cursor_month > 12:
            cursor_month = 1
            cursor_year += 1

        while (cursor_year, cursor_month) < (end.year, end.month):
            total += price
            cursor_month += 1
            if cursor_month > 12:
                cursor_month = 1
                cursor_year += 1

        return total.quantize(Decimal("0.01"))

    def total_paid(self):
        from django.db.models import Sum

        result = self.payments.aggregate(total=Sum("amount"))["total"]
        return result or 0

    def debt(self):
        return self.total_charged() - self.total_paid()

    def __str__(self):
        return f"{self.user} — {self.spot} ({self.start_date} do {self.end_date})"

    class Meta:
        verbose_name = "Pretplata"
        verbose_name_plural = "Pretplate"
        ordering = ["-start_date"]


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = "cash", "Gotovina"
        BANK_TRANSFER = "bank_transfer", "Prenos"
        CARD = "card", "Kartica"
        OTHER = "other", "Ostalo"

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name="Pretplata",
    )
    amount = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Iznos")
    paid_date = models.DateField(default=timezone.now, verbose_name="Datum uplate")
    method = models.CharField(
        max_length=20,
        choices=Method.choices,
        default=Method.CASH,
        verbose_name="Način plaćanja",
    )
    note = models.TextField(blank=True, verbose_name="Napomena")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Datum kreiranja")

    def __str__(self):
        return f"{self.subscription.user} — {self.amount} RSD ({self.paid_date.strftime('%d.%m.%Y')})"

    class Meta:
        verbose_name = "Uplata"
        verbose_name_plural = "Uplate"
        ordering = ["-paid_date"]


class AuditLog(models.Model):
    """Beleži sve izmene u sistemu — ko je šta uradio i kada."""

    class Action(models.TextChoices):
        CREATE = "create", "Kreiranje"
        UPDATE = "update", "Izmena"
        DELETE = "delete", "Brisanje"
        PAYMENT = "payment", "Uplata"
        CANCEL = "cancel", "Otkazivanje"

    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        verbose_name="Izvršio",
    )
    action = models.CharField(
        max_length=20, choices=Action.choices, verbose_name="Akcija"
    )

    # GenericForeignKey — može pokazivati na bilo koji model (ParkingUser, Subscription, Payment...)
    content_type = models.ForeignKey(
        ContentType, on_delete=models.SET_NULL, null=True, blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey("content_type", "object_id")

    description = models.TextField(verbose_name="Opis")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Vreme")

    def __str__(self):
        who = (
            self.performed_by.get_full_name() or self.performed_by.username
            if self.performed_by
            else "Sistem"
        )
        return f"[{self.timestamp.strftime('%d.%m.%Y %H:%M')}] {who} — {self.get_action_display()}: {self.description}"

    class Meta:
        verbose_name = "Zapis aktivnosti"
        verbose_name_plural = "Zapisi aktivnosti"
        ordering = ["-timestamp"]
