from django.core.exceptions import ValidationError
from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from django.db.models import Q, Sum
from django.utils import timezone
from django.urls import reverse
from django.contrib import messages
from .models import ParkingUser, ParkingSpot, Payment, ParkingConfig, Subscription
from .forms import (
    ParkingUserForm,
    ParkingSpotForm,
    ParkingConfigForm,
    PaymentForm,
    SubscriptionForm,
)
from django.db import models, transaction
import re


def _natural_sort_spots(qs):
    """Sort a queryset of ParkingSpot objects by number using natural sorting."""
    def natural_sort_key(s):
        return [
            int(part) if part.isdigit() else part.lower()
            for part in re.split(r'(\d+)', s)
        ]
    spots_list = list(qs)
    spots_list.sort(key=lambda spot: natural_sort_key(spot.number))
    return spots_list


def index(request):
    today = timezone.now().date()

    # ── Spot stats ────────────────────────────────────────────────────────────
    total_spots = ParkingSpot.objects.filter(is_active=True).count()

    occupied_spots = (
        ParkingSpot.objects.filter(
            is_active=True,
            subscriptions__start_date__lte=today,
        )
        .filter(
            models.Q(subscriptions__auto_renew=True)
            | models.Q(subscriptions__end_date__gte=today)
        )
        .distinct()
        .count()
    )
    free_spots = total_spots - occupied_spots
    free_pct = round((free_spots / total_spots * 100) if total_spots else 0)
    occupied_pct = round((occupied_spots / total_spots * 100) if total_spots else 0)

    # ── Default monthly price ─────────────────────────────────────────────────
    config = ParkingConfig.get()
    default_price = config.monthly_price if config else None

    # ── Total debt: all subscriptions' total_charged minus all payments ──────
    total_charged = sum(s.total_charged() for s in Subscription.objects.all())
    total_paid = Payment.objects.aggregate(total=Sum("amount"))["total"] or 0
    total_debt = total_charged - total_paid

    # ── Last 3 payments for dashboard card ───────────────────────────────────
    last_three_payments = (
        Payment.objects.select_related("user")
        .filter(user__isnull=False)
        .order_by("-paid_date", "-created_at")[:3]
    )

    # ── Spots with subscription info for table ────────────────────────────────
    spots_qs = ParkingSpot.objects.prefetch_related("subscriptions__user")
    spots = _natural_sort_spots(spots_qs)

    stats = {
        "total_spots": total_spots,
        "free_spots": free_spots,
        "occupied_spots": occupied_spots,
        "free_pct": free_pct,
        "occupied_pct": occupied_pct,
        "default_price": default_price,
        "total_debt": total_debt,
    }

    return render(
        request,
        "home/index.html",
        {
            "stats": stats,
            "last_three_payments": last_three_payments,
            "alerts": [],
            "users_with_subs": spots,
        },
    )


def users(request):
    parking_users = ParkingUser.objects.prefetch_related(
        "subscriptions__spot",
    ).all()

    return render(
        request,
        "home/users.html",
        {"parking_users": parking_users},
    )


def create_user_form(request):
    return render(
        request, "home/partials/create_user_form.html", {"form": ParkingUserForm()}
    )


@require_POST
def create_user(request):
    form = ParkingUserForm(request.POST)
    if form.is_valid():
        form.save()
        response = HttpResponse(status=204)
        response["HX-Trigger"] = (
            '{"showToast": {"type": "success", "message": "Korisnik uspesno kreiran!"}, "closeModal": {"refreshId": "user-list"}}'
        )
        return response
    return render(request, "home/partials/create_user_form.html", {"form": form})


def user_list(request):
    q = request.GET.get("q", "").strip()
    parking_users = ParkingUser.objects.prefetch_related(
        "subscriptions__spot",
    ).all()
    if q:
        parking_users = parking_users.filter(
            Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(plate__icontains=q)
            | Q(phone__icontains=q)
        )
    return render(
        request, "home/partials/user_list.html", {"parking_users": parking_users}
    )


def user_detail(request, pk):
    user = get_object_or_404(
        ParkingUser.objects.prefetch_related(
            "subscriptions__spot",
        ),
        pk=pk,
    )
    subscriptions = user.subscriptions.all().order_by("-start_date")
    payments = Payment.objects.filter(user=user).order_by("-paid_date", "-created_at")

    return render(
        request,
        "home/user_detail.html",
        {
            "user": user,
            "subscriptions": subscriptions,
            "payments": payments,
            "debt": user.total_debt(),
        },
    )


def edit_user_form(request, pk):
    user = get_object_or_404(ParkingUser, pk=pk)
    form = ParkingUserForm(instance=user)
    return render(
        request, "home/partials/edit_user_form.html", {"form": form, "user": user}
    )


@require_POST
def edit_user(request, pk):
    user = get_object_or_404(ParkingUser, pk=pk)
    form = ParkingUserForm(request.POST, instance=user)
    if form.is_valid():
        form.save()
        detail_url = reverse("home:user_detail", kwargs={"pk": user.pk})
        messages.success(request, "Izmene sačuvane!")
        script = f"""
        <script>
            window.location.href = '{detail_url}';
        </script>
        """
        return HttpResponse(script)
    return render(
        request, "home/partials/edit_user_form.html", {"form": form, "user": user}
    )


def create_payment_form(request, pk):
    user = get_object_or_404(ParkingUser, pk=pk)
    from datetime import date

    form = PaymentForm(initial={"paid_date": date.today()})
    return render(
        request,
        "home/partials/create_payment_form.html",
        {"form": form, "user": user},
    )


@require_POST
def create_payment(request, pk):
    user = get_object_or_404(ParkingUser, pk=pk)
    form = PaymentForm(request.POST)
    if form.is_valid():
        payment = form.save(commit=False)
        payment.user = user
        payment.save()
        detail_url = reverse("home:user_detail", kwargs={"pk": user.pk})
        messages.success(request, "Uplata uspešno sačuvana!")
        script = f"""
        <script>
            window.location.href = '{detail_url}';
        </script>
        """
        return HttpResponse(script)
    return render(
        request,
        "home/partials/create_payment_form.html",
        {"form": form, "user": user},
    )


def edit_payment_form(request, payment_pk):
    payment = get_object_or_404(Payment, pk=payment_pk)
    form = PaymentForm(instance=payment)
    return render(
        request,
        "home/partials/edit_payment_form.html",
        {"form": form, "payment": payment},
    )


@require_POST
def edit_payment(request, payment_pk):
    payment = get_object_or_404(Payment, pk=payment_pk)
    form = PaymentForm(request.POST, instance=payment)
    if form.is_valid():
        form.save()
        detail_url = reverse("home:user_detail", kwargs={"pk": payment.user.pk})
        messages.success(request, "Uplata uspešno izmenjena!")
        script = f"""
        <script>
            window.location.href = '{detail_url}';
        </script>
        """
        return HttpResponse(script)
    return render(
        request,
        "home/partials/edit_payment_form.html",
        {"form": form, "payment": payment},
    )


def create_subscription_form(request, pk):
    user = get_object_or_404(ParkingUser, pk=pk)
    form = SubscriptionForm()
    return render(
        request,
        "home/partials/create_subscription_form.html",
        {"form": form, "user": user},
    )


@require_POST
def create_subscription(request, pk):
    user = get_object_or_404(ParkingUser, pk=pk)
    form = SubscriptionForm(request.POST)
    if form.is_valid():
        subscription = form.save(commit=False)
        subscription.user = user
        subscription.auto_renew = subscription.end_date is None
        try:
            with transaction.atomic():
                subscription.full_clean()
                subscription.save()
        except ValidationError as e:
            form.add_error(None, e.messages)
            return render(
                request,
                "home/partials/create_subscription_form.html",
                {"form": form, "user": user},
            )
        detail_url = reverse("home:user_detail", kwargs={"pk": user.pk})
        messages.success(request, "Pretplata uspešno kreirana!")
        script = f"""
        <script>
            window.location.href = '{detail_url}';
        </script>
        """
        return HttpResponse(script)
    return render(
        request,
        "home/partials/create_subscription_form.html",
        {"form": form, "user": user},
    )


def edit_subscription_form(request, sub_pk):
    subscription = get_object_or_404(Subscription, pk=sub_pk)
    form = SubscriptionForm(instance=subscription)
    return render(
        request,
        "home/partials/edit_subscription_form.html",
        {"form": form, "subscription": subscription},
    )


@require_POST
def edit_subscription(request, sub_pk):
    subscription = get_object_or_404(Subscription, pk=sub_pk)
    form = SubscriptionForm(request.POST, instance=subscription)
    if form.is_valid():
        subscription = form.save(commit=False)
        subscription.auto_renew = subscription.end_date is None
        try:
            with transaction.atomic():
                subscription.full_clean()
                subscription.save()
        except ValidationError as e:
            form.add_error(None, e.messages)
            return render(
                request,
                "home/partials/edit_subscription_form.html",
                {"form": form, "subscription": subscription},
            )
        detail_url = reverse("home:user_detail", kwargs={"pk": subscription.user.pk})
        messages.success(request, "Pretplata uspešno izmenjena!")
        script = f"""
        <script>
            window.location.href = '{detail_url}';
        </script>
        """
        return HttpResponse(script)
    return render(
        request,
        "home/partials/edit_subscription_form.html",
        {"form": form, "subscription": subscription},
    )


def get_spots_queryset(q=None):
    qs = ParkingSpot.objects.prefetch_related("subscriptions__user")

    if q:
        qs = qs.filter(number__icontains=q)

    return _natural_sort_spots(qs)


def spots(request):
    parking_spots = get_spots_queryset()

    return render(
        request,
        "home/spots.html",
        {
            "parking_spots": parking_spots,
            "total_count": len(parking_spots),
            "active_count": sum(1 for spot in parking_spots if spot.is_active),
        },
    )


def spot_list(request):
    q = request.GET.get("q", "").strip()
    parking_spots = get_spots_queryset(q)

    return render(
        request,
        "home/partials/spot_list.html",
        {"parking_spots": parking_spots},
    )


def create_spot_form(request):
    return render(
        request, "home/partials/create_spot_form.html", {"form": ParkingSpotForm()}
    )


@require_POST
def create_spot(request):
    form = ParkingSpotForm(request.POST)
    if form.is_valid():
        form.save()
        response = HttpResponse(status=204)
        response["HX-Trigger"] = (
            '{"showToast": {"type": "success", "message": "Parking mesto kreirano!"}, "closeModal": {"refreshId": "spot-list"}}'
        )
        return response
    return render(request, "home/partials/create_spot_form.html", {"form": form})


def edit_spot_form(request, pk):
    spot = get_object_or_404(ParkingSpot, pk=pk)
    form = ParkingSpotForm(instance=spot)
    return render(
        request, "home/partials/edit_spot_form.html", {"form": form, "spot": spot}
    )


@require_POST
def edit_spot(request, pk):
    spot = get_object_or_404(ParkingSpot, pk=pk)
    form = ParkingSpotForm(request.POST, instance=spot)

    if form.is_valid():
        form.save()
        # Vraćamo prazan odgovor sa script tagom koji okida događaje na klijentu
        script = """
        <script>
            showToast('success', 'Izmene sačuvane!');
            document.body.dispatchEvent(new CustomEvent('closeModal', {
                detail: { refreshId: 'spot-list' }
            }));
        </script>
        """
        return HttpResponse(script)

    return render(
        request, "home/partials/edit_spot_form.html", {"form": form, "spot": spot}
    )


def pricing_config_form(request):
    config = ParkingConfig.objects.filter(pk=1).first()
    if config:
        form = ParkingConfigForm(instance=config)
    else:
        form = ParkingConfigForm()
    return render(
        request,
        "home/partials/pricing_config_form.html",
        {"form": form, "config": config},
    )


@require_POST
def save_pricing_config(request):
    config = ParkingConfig.objects.filter(pk=1).first()
    if config:
        form = ParkingConfigForm(request.POST, instance=config)
    else:
        form = ParkingConfigForm(request.POST)

    if form.is_valid():
        form.save()
        config = ParkingConfig.objects.get(pk=1)
        card_html = render_to_string(
            "home/partials/pricing_config_card.html",
            {"default_price": config.monthly_price},
            request=request,
        )
        oob_card = card_html.replace(
            'id="pricing-config-card"',
            'id="pricing-config-card" hx-swap-oob="true"',
            1,
        )
        script = f"""
        <script>
            showToast('success', 'Mesečna cena je sačuvana!');
            document.body.dispatchEvent(new CustomEvent('closeModal', {{
                detail: {{ refreshId: null }}
            }}));
        </script>
        {oob_card}
        """
        return HttpResponse(script)

    return render(
        request,
        "home/partials/pricing_config_form.html",
        {"form": form, "config": config},
    )


def help(request):
    return render(request, "home/help.html")
