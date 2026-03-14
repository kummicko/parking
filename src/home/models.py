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
        max_length=20, unique=True, verbose_name="Registarska oznaka"
    )
    notes = models.TextField(blank=True, verbose_name="Napomena")
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Datum registracije"
    )

    def active_subscriptions(self):
        """Sve aktivne pretplate korisnika (može ih biti više)."""
        return self.subscriptions.filter(status=Subscription.Status.ACTIVE)

    def total_debt(self):
        """Ukupan dug korisnika po svim aktivnim pretplatama."""
        return sum(s.debt() for s in self.active_subscriptions())

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        verbose_name = "Korisnik parkinga"
        verbose_name_plural = "Korisnici parkinga"
        ordering = ["last_name", "first_name"]


class ParkingSpot(models.Model):
    number = models.PositiveIntegerField(
        unique=True, editable=False, verbose_name="Broj mesta"
    )
    is_active = models.BooleanField(default=True, verbose_name="Aktivno")
    notes = models.TextField(blank=True, verbose_name="Napomena")

    def save(self, *args, **kwargs):
        if not self.number:
            existing = set(ParkingSpot.objects.values_list("number", flat=True))
            n = 1
            while n in existing:
                n += 1
            self.number = n
        super().save(*args, **kwargs)

    def is_available(self):
        return not self.subscriptions.filter(status=Subscription.Status.ACTIVE).exists()

    def __str__(self):
        return f"Mesto {self.number}"

    class Meta:
        verbose_name = "Parking mesto"
        verbose_name_plural = "Parking mesta"
        ordering = ["number"]


class Subscription(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Na čekanju"
        ACTIVE = "active", "Aktivna"
        EXPIRED = "expired", "Istekla"
        CANCELLED = "cancelled", "Otkazana"

    user = models.ForeignKey(
        ParkingUser,
        on_delete=models.CASCADE,
        related_name="subscriptions",
        verbose_name="Korisnik",
    )
    spot = models.ForeignKey(
        ParkingSpot,
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
        default=True, verbose_name="Automatsko obnavljanje"
    )
    monthly_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Mesečna cena",
        help_text="Ostavite prazno za podrazumevanu cenu",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name="Status",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Datum kreiranja")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Datum izmene")

    def save(self, *args, **kwargs):
        if not self.monthly_price:
            self.monthly_price = ParkingConfig.get().monthly_price
        super().save(*args, **kwargs)

    def is_active_for_month(self, year, month):
        """Da li je pretplata aktivna za dati mesec."""
        from datetime import date

        month_start = date(year, month, 1)
        if self.status != self.Status.ACTIVE:
            return False
        if self.start_date > month_start:
            return False
        if not self.auto_renew and self.end_date and self.end_date < month_start:
            return False
        return True

    def cancel(self):
        """Otkaži pretplatu — neće se obnavljati."""
        self.auto_renew = False
        self.status = self.Status.CANCELLED
        self.end_date = timezone.now().date()
        self.save()

    def is_expired(self):
        if self.auto_renew:
            return False
        return self.end_date and self.end_date < timezone.now().date()

    def total_charged(self):
        """Ukupan iznos koji korisnik treba da plati od početka do danas.

        Prvi i poslednji mesec se računaju srazmerno broju dana korišćenja.
        Svi meseci između se naplaćuju u punom iznosu.
        """
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

        # isti mesec — naplati srazmerno
        if start.year == end.year and start.month == end.month:
            days_in_month = calendar.monthrange(start.year, start.month)[1]
            days_used = (end - start).days + 1
            total += price * Decimal(days_used) / Decimal(days_in_month)
            return total.quantize(Decimal("0.01"))

        # prvi mesec — od start_date do kraja meseca
        days_in_first = calendar.monthrange(start.year, start.month)[1]
        days_used_first = days_in_first - start.day + 1
        total += price * Decimal(days_used_first) / Decimal(days_in_first)

        # poslednji mesec — od prvog do end date
        days_in_last = calendar.monthrange(end.year, end.month)[1]
        total += price * Decimal(end.day) / Decimal(days_in_last)

        # puni meseci između
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
        """Ukupan iznos svih uplata."""
        from django.db.models import Sum

        result = self.payments.aggregate(total=Sum("amount"))["total"]
        return result or 0

    def debt(self):
        """Dug u valuti. Pozitivan = duguje, negativan = plaćeno unapred."""
        return self.total_charged() - self.total_paid()

    def __str__(self):
        return f"{self.user} — {self.spot} ({self.start_date} do {self.end_date})"

    class Meta:
        verbose_name = "Pretplata"
        verbose_name_plural = "Pretplate"
        ordering = ["-start_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["spot"],
                condition=models.Q(status="active"),
                name="unique_active_subscription_per_spot",
            )
        ]


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
    period_from = models.DateField(verbose_name="Period od")
    period_to = models.DateField(verbose_name="Period do")
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

    @property
    def months_covered(self):
        """Broj meseci koje ova uplata pokriva."""
        return (
            (self.period_to.year - self.period_from.year) * 12
            + (self.period_to.month - self.period_from.month)
            + 1
        )

    def __str__(self):
        if (
            self.period_from.month == self.period_to.month
            and self.period_from.year == self.period_to.year
        ):
            return f"{self.subscription.user} — {self.period_from.strftime('%m/%Y')}"
        return f"{self.subscription.user} — {self.period_from.strftime('%m/%Y')} do {self.period_to.strftime('%m/%Y')}"

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
