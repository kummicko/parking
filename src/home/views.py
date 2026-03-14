from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from django.db.models import Sum, Q
from django.utils import timezone
from .models import ParkingUser, ParkingSpot, Subscription, Payment
from .forms import ParkingUserForm


def index(request):
    today = timezone.now().date()

    # ── Spot stats ────────────────────────────────────────────────────────────
    total_spots = ParkingSpot.objects.filter(is_active=True).count()

    occupied_spots = (
        ParkingSpot.objects.filter(
            is_active=True, subscriptions__status=Subscription.Status.ACTIVE
        )
        .distinct()
        .count()
    )

    free_spots = total_spots - occupied_spots
    free_pct = round((free_spots / total_spots * 100) if total_spots else 0)
    occupied_pct = round((occupied_spots / total_spots * 100) if total_spots else 0)

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

    stats = {
        "total_spots": total_spots,
        "free_spots": free_spots,
        "occupied_spots": occupied_spots,
        "free_pct": free_pct,
        "occupied_pct": occupied_pct,
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
        response = HttpResponse(status=204)
        response["HX-Trigger"] = (
            '{"showToast": {"type": "success", "message": "Korisnik uspesno izmenjen!"}, "closeModal": {"refreshId": "user-list"}}'
        )
        return response
    return render(
        request, "home/partials/edit_user_form.html", {"form": form, "user": user}
    )
