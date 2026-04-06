from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from django.db.models import Sum, Q
from django.utils import timezone
from .models import ParkingUser, ParkingSpot, Payment, ParkingConfig
from .forms import ParkingUserForm, ParkingSpotForm, ParkingConfigForm
from django.db import models


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
    try:
        default_price = ParkingConfig.get().monthly_price
    except (ValueError, ParkingConfig.DoesNotExist):
        default_price = None

    # ── Revenue ───────────────────────────────────────────────────────────────
    revenue_today = (
        Payment.objects.filter(paid_date=today).aggregate(total=Sum("amount"))["total"]
        or 0
    )
    sessions_today = Payment.objects.filter(paid_date=today).count()

    # ── Total debt across all users ───────────────────────────────────────────
    users = ParkingUser.objects.prefetch_related(
        "subscriptions__payments",
        "subscriptions__spot",
    ).all()

    total_debt = sum(u.total_debt() for u in users)

    # ── Recent payments (last 10) ─────────────────────────────────────────────
    recent_payments = Payment.objects.select_related(
        "subscription__user", "subscription__spot"
    ).order_by("-paid_date", "-created_at")[:10]

    # ── Spots with subscription info for table ────────────────────────────────
    spots = ParkingSpot.objects.prefetch_related(
        "subscriptions__user",
        "subscriptions__payments",
    ).order_by("number")

    stats = {
        "total_spots": total_spots,
        "free_spots": free_spots,
        "occupied_spots": occupied_spots,
        "free_pct": free_pct,
        "occupied_pct": occupied_pct,
        "default_price": default_price,
        "revenue_today": revenue_today,
        "sessions_today": sessions_today,
        "total_debt": total_debt,
    }

    return render(
        request,
        "home/index.html",
        {
            "stats": stats,
            "recent_payments": recent_payments,
            "alerts": [],
            "users_with_subs": spots,
        },
    )


def users(request):
    parking_users = ParkingUser.objects.prefetch_related(
        "subscriptions__payments",
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
        "subscriptions__payments",
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
        # Vraćamo prazan odgovor sa script tagom koji okida događaje na klijentu
        script = """
        <script>
            showToast('success', 'Izmene sačuvane!');
            document.body.dispatchEvent(new CustomEvent('closeModal', {
                detail: { refreshId: 'user-list' }
            }));
        </script>
        """
        return HttpResponse(script)
    return render(
        request, "home/partials/edit_user_form.html", {"form": form, "user": user}
    )


def get_spots_queryset(q=None):
    qs = ParkingSpot.objects.prefetch_related("subscriptions__user")

    if q:
        qs = qs.filter(number__icontains=q)

    return qs


def spots(request):
    parking_spots = get_spots_queryset()

    return render(
        request,
        "home/spots.html",
        {
            "parking_spots": parking_spots,
            "total_count": parking_spots.count(),
            "active_count": parking_spots.filter(is_active=True).count(),
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
