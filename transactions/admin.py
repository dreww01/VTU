from datetime import timedelta

from django.contrib import admin, messages
from django.db.models import Sum
from django.utils import timezone
from django.utils.html import format_html

from .models import AppSettings, Transaction
from .providers.exceptions import VTPassError
from .services.vtu_service import check_and_get_transaction_status


class AppSettingsAdmin(admin.ModelAdmin):
    """Admin interface for app-wide settings"""

    fieldsets = (
        (
            "Fraud Detection",
            {
                "fields": ("fraud_checks_enabled",),
                "description": "Toggle fraud detection checks on/off. Useful for testing.",
            },
        ),
        (
            "Maintenance",
            {"fields": ("maintenance_mode",), "description": "Put the app in maintenance mode."},
        ),
    )

    def has_add_permission(self, request):
        """Only allow one settings instance"""
        return not AppSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion"""
        return False


# Register it
admin.site.register(AppSettings, AppSettingsAdmin)


@admin.action(description="Mark selected transactions as COMPLETED")
def mark_as_completed(modeladmin, request, queryset):
    """Manually mark transactions as completed"""
    updated = queryset.update(status="completed")
    modeladmin.message_user(
        request, f"{updated} transaction(s) marked as completed.", messages.SUCCESS
    )


@admin.action(description="Mark selected transactions as FAILED")
def mark_as_failed(modeladmin, request, queryset):
    """Manually mark transactions as failed"""
    updated = queryset.update(status="failed")
    modeladmin.message_user(
        request, f"{updated} transaction(s) marked as failed.", messages.SUCCESS
    )


@admin.action(description="Recheck status with VTPass API")
def recheck_with_vtpass(modeladmin, request, queryset):
    """Check transaction status directly from VTPass"""
    checked = 0
    completed = 0
    failed = 0
    still_pending = 0
    errors = 0

    for tx in queryset:
        checked += 1
        try:
            vtpass_status = check_and_get_transaction_status(tx.reference)

            if vtpass_status is None:
                # Transaction doesn't exist on VTPass
                tx.status = "failed"
                tx.save()
                failed += 1
            elif vtpass_status == "completed":
                tx.status = "completed"
                tx.save()
                completed += 1
            elif vtpass_status == "failed":
                tx.status = "failed"
                tx.save()
                failed += 1
            else:
                # Still pending on VTPass
                still_pending += 1

        except VTPassError as e:
            errors += 1
            modeladmin.message_user(
                request, f"Error checking {tx.reference}: {str(e)}", messages.ERROR
            )

    # Show detailed summary
    msg = f"Checked {checked} transaction(s): {completed} completed, {failed} failed"
    if still_pending > 0:
        msg += f", {still_pending} still pending"
    if errors > 0:
        msg += f", {errors} errors"

    modeladmin.message_user(request, msg, messages.SUCCESS)


class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        "reference",
        "wallet_user",
        "transaction_type",
        "amount_display",
        "status_badge",
        "timestamp_display",
        "description_short",
    ]

    list_filter = [
        "status",
        "transaction_type",
        "timestamp",
    ]

    search_fields = [
        "reference",
        "wallet__user__username",
        "wallet__user__email",
        "description",
    ]

    readonly_fields = [
        "reference",
        "timestamp",
        "wallet",
        "amount",
        "transaction_type",
        "description",
        "token",
    ]

    actions = [
        mark_as_completed,
        mark_as_failed,
        recheck_with_vtpass,
    ]

    list_per_page = 50
    date_hierarchy = "timestamp"

    # Add fieldsets for better organization in detail view
    fieldsets = (
        ("Transaction Info", {"fields": ("reference", "transaction_type", "status", "timestamp")}),
        ("User & Amount", {"fields": ("wallet", "amount")}),
        (
            "Details",
            {
                "fields": ("description", "token"),
                "classes": ("collapse",),
            },
        ),
    )

    def wallet_user(self, obj):
        """Display the username of the wallet owner"""
        return obj.wallet.user.username

    wallet_user.short_description = "User"
    wallet_user.admin_order_field = "wallet__user__username"

    def amount_display(self, obj):
        """Display amount with currency"""
        return f"NGN {obj.amount:,.2f}"

    amount_display.short_description = "Amount"
    amount_display.admin_order_field = "amount"

    def timestamp_display(self, obj):
        """Display human-readable timestamp"""
        from django.utils.safestring import mark_safe

        now = timezone.now()
        diff = now - obj.timestamp

        if diff < timedelta(minutes=1):
            return mark_safe('<span style="color: #28a745;">Just now</span>')
        elif diff < timedelta(hours=1):
            minutes = int(diff.total_seconds() / 60)
            return format_html('<span style="color: #28a745;">{} min ago</span>', minutes)
        elif diff < timedelta(days=1):
            hours = int(diff.total_seconds() / 3600)
            return format_html('<span style="color: #FFA500;">{} hrs ago</span>', hours)
        else:
            return obj.timestamp.strftime("%Y-%m-%d %H:%M")

    timestamp_display.short_description = "Time"
    timestamp_display.admin_order_field = "timestamp"

    def status_badge(self, obj):
        """Display status with color badges"""
        colors = {
            "pending": "#FFA500",  # Orange
            "completed": "#28a745",  # Green
            "failed": "#dc3545",  # Red
        }
        color = colors.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.status.upper(),
        )

    status_badge.short_description = "Status"
    status_badge.admin_order_field = "status"

    def description_short(self, obj):
        """Show shortened description"""
        if obj.description and len(obj.description) > 50:
            return obj.description[:50] + "..."
        return obj.description or "-"

    description_short.short_description = "Description"

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of transactions"""
        return False

    def changelist_view(self, request, extra_context=None):
        """Add summary statistics to the admin list view"""
        extra_context = extra_context or {}

        # Calculate statistics
        total = Transaction.objects.count()
        pending = Transaction.objects.filter(status="pending").count()
        completed = Transaction.objects.filter(status="completed").count()
        failed = Transaction.objects.filter(status="failed").count()

        # Today's transactions
        today = timezone.now().date()
        today_total = (
            Transaction.objects.filter(timestamp__date=today).aggregate(total=Sum("amount"))[
                "total"
            ]
            or 0
        )

        extra_context["total_transactions"] = total
        extra_context["pending_count"] = pending
        extra_context["completed_count"] = completed
        extra_context["failed_count"] = failed
        extra_context["today_total"] = today_total

        return super().changelist_view(request, extra_context)


# Register the admin
admin.site.register(Transaction, TransactionAdmin)
