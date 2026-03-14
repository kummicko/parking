from django.contrib import admin
from django.utils.html import format_html

from .models import (
    AuditLog,
    ParkingConfig,
    ParkingSpot,
    ParkingUser,
    Payment,
    Subscription,
)


# ──────────────────────────────────────────────
# ParkingConfig (singleton)
# ──────────────────────────────────────────────


@admin.register(ParkingConfig)
class ParkingConfigAdmin(admin.ModelAdmin):
    fields = ("monthly_price", "updated_at")
    readonly_fields = ("updated_at",)

    def has_add_permission(self, request):
        # Allow adding only if the singleton doesn't exist yet
        return not ParkingConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


# ──────────────────────────────────────────────
# ParkingSpot
# ──────────────────────────────────────────────


@admin.register(ParkingSpot)
class ParkingSpotAdmin(admin.ModelAdmin):
    list_display = ("number", "is_active", "available_display", "notes")
    list_filter = ("is_active",)
    search_fields = ("number", "notes")
    readonly_fields = ("number",)

    @admin.display(description="Slobodno", boolean=True)
    def available_display(self, obj):
        return obj.is_available()


# ──────────────────────────────────────────────
# Payment inline (used inside Subscription)
# ──────────────────────────────────────────────


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    fields = ("period_from", "period_to", "amount", "method", "paid_date", "note")
    ordering = ("-paid_date",)


# ──────────────────────────────────────────────
# Subscription
# ──────────────────────────────────────────────


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "spot",
        "status",
        "start_date",
        "end_date",
        "auto_renew",
        "monthly_price",
        "charged_display",
        "paid_display",
        "debt_display",
    )
    list_filter = ("status", "auto_renew", "spot")
    search_fields = (
        "user__first_name",
        "user__last_name",
        "user__plate",
        "spot__number",
    )
    autocomplete_fields = ("user", "spot")
    readonly_fields = (
        "created_at",
        "updated_at",
        "charged_display",
        "paid_display",
        "debt_display",
    )
    inlines = [PaymentInline]

    fieldsets = (
        (
            None,
            {
                "fields": ("user", "spot", "status", "auto_renew"),
            },
        ),
        (
            "Period",
            {
                "fields": ("start_date", "end_date", "monthly_price"),
            },
        ),
        (
            "Finansije",
            {
                "fields": ("charged_display", "paid_display", "debt_display"),
            },
        ),
        (
            "Metapodaci",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="Zaduženo (RSD)")
    def charged_display(self, obj):
        if not obj.pk or not obj.start_date or not obj.monthly_price:
            return "—"
        return obj.total_charged()

    @admin.display(description="Plaćeno (RSD)")
    def paid_display(self, obj):
        if not obj.pk:
            return "—"
        return obj.total_paid()

    @admin.display(description="Dug (RSD)")
    def debt_display(self, obj):
        if not obj.pk or not obj.start_date or not obj.monthly_price:
            return "—"
        debt = obj.debt()
        if debt > 0:
            return format_html(
                '<span style="color:red;font-weight:bold">{}</span>', debt
            )
        elif debt < 0:
            return format_html('<span style="color:green">{}</span>', debt)
        return debt


# ──────────────────────────────────────────────
# ParkingUser
# ──────────────────────────────────────────────


class SubscriptionInline(admin.TabularInline):
    model = Subscription
    extra = 0
    fields = ("spot", "status", "start_date", "end_date", "auto_renew", "monthly_price")
    readonly_fields = ("status",)
    show_change_link = True


@admin.register(ParkingUser)
class ParkingUserAdmin(admin.ModelAdmin):
    list_display = (
        "last_name",
        "first_name",
        "plate",
        "phone",
        "email",
        "active_sub_count",
        "total_debt_display",
        "created_at",
    )
    search_fields = ("first_name", "last_name", "plate", "phone", "email")
    readonly_fields = ("created_at",)
    inlines = [SubscriptionInline]

    fieldsets = (
        (
            None,
            {
                "fields": ("first_name", "last_name", "plate"),
            },
        ),
        (
            "Kontakt",
            {
                "fields": ("phone", "email"),
            },
        ),
        (
            "Ostalo",
            {
                "fields": ("notes", "created_at"),
            },
        ),
    )

    @admin.display(description="Aktivne pretplate")
    def active_sub_count(self, obj):
        return obj.active_subscriptions().count()

    @admin.display(description="Ukupan dug (RSD)")
    def total_debt_display(self, obj):
        debt = obj.total_debt()
        if debt > 0:
            return format_html(
                '<span style="color:red;font-weight:bold">{}</span>', debt
            )
        elif debt < 0:
            return format_html('<span style="color:green">{}</span>', debt)
        return debt


# ──────────────────────────────────────────────
# Payment
# ──────────────────────────────────────────────


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "subscription",
        "period_from",
        "period_to",
        "months_covered_display",
        "amount",
        "method",
        "paid_date",
    )
    list_filter = ("method", "paid_date")
    search_fields = (
        "subscription__user__first_name",
        "subscription__user__last_name",
        "subscription__user__plate",
    )
    autocomplete_fields = ("subscription",)
    readonly_fields = ("created_at", "months_covered_display")

    @admin.display(description="Pokriveno meseci")
    def months_covered_display(self, obj):
        return obj.months_covered


# ──────────────────────────────────────────────
# AuditLog (read-only)
# ──────────────────────────────────────────────


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "performed_by", "action", "description")
    list_filter = ("action", "performed_by")
    search_fields = ("description", "performed_by__username")
    readonly_fields = (
        "timestamp",
        "performed_by",
        "action",
        "content_type",
        "object_id",
        "description",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
