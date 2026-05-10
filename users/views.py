from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model, login
from django.utils import timezone
from django.db.models import Sum, Count, Q
from datetime import date, timedelta
from calendar import month_abbr

from .forms import CustomUserCreationForm
from maintenance.models import MaintenanceRequest
from notifications.models import Notification

User = get_user_model()


def get_user_notifications(user):
    return Notification.objects.filter(user=user).order_by("-created_at")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _last_6_months():
    """Return list of (year, month, label) for the last 6 months, oldest first."""
    today = date.today()
    months = []
    for i in range(5, -1, -1):
        # go back i months
        first_of_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        # simpler arithmetic
        month = (today.month - i - 1) % 12 + 1
        year  = today.year + ((today.month - i - 1) // 12)
        months.append((year, month, month_abbr[month]))
    return months


def _build_monthly_series(queryset, date_field, amount_field, months):
    """
    Aggregate a queryset by month into a list aligned with `months`.
    months: list of (year, month, label)
    Returns list of floats.
    """
    result = []
    for year, month, _ in months:
        total = queryset.filter(
            **{f"{date_field}__year": year, f"{date_field}__month": month}
        ).aggregate(s=Sum(amount_field))["s"] or 0
        result.append(float(total))
    return result


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@login_required
def dashboard_view(request):
    user = request.user
    context = {}

    # Unread notification count (shared by all roles)
    unread_count = Notification.objects.filter(user=user, is_read=False).count()
    context["unread_count"] = unread_count

    # -----------------------------------------------------------------------
    # LANDLORD
    # -----------------------------------------------------------------------
    if user.role == "landlord":
        from contracts.models import Contract
        from payments.models import Payment
        from properties.models import Property

        properties  = Property.objects.filter(owner=user)
        contracts   = Contract.objects.filter(landlord=user, status="active")
        all_payments = Payment.objects.filter(contract__landlord=user)

        # ── Stat cards ──
        total_revenue = (
            all_payments.filter(status="paid")
            .aggregate(total=Sum("amount"))["total"] or 0
        )
        active_tenants  = contracts.count()
        total_units     = properties.count()
        occupied_units  = properties.filter(status="rented").count()
        available_units = properties.filter(status="available").count()
        occupancy_pct   = round(occupied_units / total_units * 100) if total_units else 0

        # ── Maintenance ──
        # MaintenanceRequest.tenant is a TenantProfile FK
        # Reach the logged-in user via contract__landlord (already filtered above)
        maintenance_qs = MaintenanceRequest.objects.filter(
            contract__landlord=user
        )
        pending_maintenance = maintenance_qs.filter(
            status__in=["open", "in_progress"]
        ).count()
        maintenance_cost = 0  # extend if you have a cost field

        # ── Chart data (last 6 months) ──
        months = _last_6_months()
        chart_labels  = [lbl for _, _, lbl in months]
        revenue_data  = _build_monthly_series(
            all_payments.filter(status="paid"), "paid_date", "amount", months
        )
        # expenses: maintenance has no cost field by default → zeros (extend as needed)
        expense_data  = [0] * 6

        # ── Recent payments ──
        recent_payments = (
            Payment.objects.filter(contract__landlord=user)
            .select_related("contract__tenant__user", "contract__property")
            .order_by("-due_date")[:8]
        )

        # ── Maintenance requests ──
        requests = maintenance_qs.select_related(
            "contract__property", "tenant"
        ).order_by("-created_at")[:8]

        context.update({
            # stats
            "total_revenue":       total_revenue,
            "active_tenants":      active_tenants,
            "total_units":         total_units,
            "occupied_units":      occupied_units,
            "available_units":     available_units,
            "occupancy_pct":       occupancy_pct,
            "pending_maintenance": pending_maintenance,
            "maintenance_cost":    maintenance_cost,
            # charts
            "chart_labels":   chart_labels,
            "revenue_data":   revenue_data,
            "expense_data":   expense_data,
            # tables
            "recent_payments": recent_payments,
            "requests":        requests,
        })

    # -----------------------------------------------------------------------
    # AGENT
    # -----------------------------------------------------------------------
    elif user.role == "agent":
        from contracts.models import Contract
        from payments.models import Payment
        from properties.models import Property

        # Listings the agent manages
        listings = Property.objects.filter(agent=user)

        # Contracts where this agent is assigned
        agent_contracts = Contract.objects.filter(agent=user)

        active_listings  = listings.filter(status="available").count()
        active_contracts = agent_contracts.filter(status="active").count()

        # Unique clients (tenants on agent contracts)
        client_count = (
            agent_contracts.filter(status="active")
            .values("tenant")
            .distinct()
            .count()
        )

        # Commission: 5 % of rent paid on agent's contracts this month
        today = date.today()
        paid_this_month = (
            Payment.objects.filter(
                contract__agent=user,
                status="paid",
                paid_date__year=today.year,
                paid_date__month=today.month,
            ).aggregate(s=Sum("amount"))["s"] or 0
        )
        monthly_commission = round(paid_this_month * 0.05, 2)

        # Chart — commission per month (5 % of paid rent)
        months = _last_6_months()
        chart_labels = [lbl for _, _, lbl in months]
        commission_data = []
        for year, month, _ in months:
            paid = (
                Payment.objects.filter(
                    contract__agent=user,
                    status="paid",
                    paid_date__year=year,
                    paid_date__month=month,
                ).aggregate(s=Sum("amount"))["s"] or 0
            )
            commission_data.append(round(float(paid) * 0.05, 2))

        # Pipeline: active contracts with property & tenant
        pipeline = (
            agent_contracts.filter(status__in=["active", "pending"])
            .select_related("property", "tenant__user")
            .order_by("-signed_at")[:6]
        )

        # Listings table
        listings_table = listings.order_by("-id")[:8]

        # Recent contracts
        recent_contracts = (
            agent_contracts.select_related("tenant__user", "property")
            .order_by("-signed_at")[:6]
        )

        context.update({
            "active_listings":    active_listings,
            "active_contracts":   active_contracts,
            "client_count":       client_count,
            "monthly_commission": monthly_commission,
            # charts
            "chart_labels":     chart_labels,
            "commission_data":  commission_data,
            # tables
            "pipeline":          pipeline,
            "listings_table":    listings_table,
            "recent_contracts":  recent_contracts,
        })

    # -----------------------------------------------------------------------
    # TENANT
    # -----------------------------------------------------------------------
    elif user.role == "tenant":
        from contracts.models import Contract
        from payments.models import Payment
        from properties.models import Property
        from django.db.models import Case, When, IntegerField

        # ── Resolve TenantProfile for this user ──
        # TenantProfile is linked to User via a OneToOne; the reverse accessor
        # on User is `profile` (as shown in the error: choices are tenant, profile).
        try:
            tenant_profile = user.profile   # User → TenantProfile (OneToOne reverse)
        except Exception:
            tenant_profile = None

        # ── Active (or most recent) contract ──
        if tenant_profile:
            tenant_contract = (
                Contract.objects.select_related("property")
                .filter(tenant=tenant_profile)
                .annotate(
                    status_order=Case(
                        When(status="active",  then=0),
                        When(status="pending", then=1),
                        default=2,
                        output_field=IntegerField(),
                    )
                )
                .order_by("status_order", "-start_date")
                .first()
            )
        else:
            tenant_contract = None

        # Attach computed lease progress to the contract object
        if tenant_contract:
            today = date.today()
            start = tenant_contract.start_date
            end   = tenant_contract.end_date
            if start and end and end > start:
                total_days     = (end - start).days
                elapsed_days   = max(0, (today - start).days)
                lease_pct      = min(100, round(elapsed_days / total_days * 100))
                days_remaining = max(0, (end - today).days)
            else:
                lease_pct      = 0
                days_remaining = 0
            tenant_contract.lease_progress_pct = lease_pct
            tenant_contract.days_remaining      = days_remaining

        # ── Days until rent is due ──
        days_until_rent = None
        if tenant_contract and tenant_contract.status == "active":
            next_payment = (
                Payment.objects.filter(
                    contract=tenant_contract,
                    status__in=["pending", "overdue"],
                )
                .order_by("due_date")
                .first()
            )
            if next_payment:
                days_until_rent = (next_payment.due_date - date.today()).days

        # ── Payment history ──
        # Filter via contract__tenant (TenantProfile), not tenant__user
        payment_filter = (
            {"contract__tenant": tenant_profile} if tenant_profile
            else {"contract__tenant__isnull": True}  # returns nothing safely
        )
        recent_payments = (
            Payment.objects.filter(**payment_filter)
            .order_by("-due_date")[:6]
        )
        payments_made = (
            Payment.objects.filter(**payment_filter, status="paid").count()
        )

        # ── Maintenance ──
        # MaintenanceRequest.tenant is the TenantProfile FK
        maint_filter = (
            {"tenant": tenant_profile} if tenant_profile
            else {"tenant__isnull": True}
        )
        my_requests = (
            MaintenanceRequest.objects.filter(**maint_filter)
            .order_by("-created_at")[:5]
        )
        total_requests = MaintenanceRequest.objects.filter(**maint_filter).count()
        open_requests  = MaintenanceRequest.objects.filter(
            **maint_filter, status__in=["open", "in_progress"]
        ).count()

        # ── Available properties to explore ──
        available_properties = Property.objects.filter(status="available")[:3]

        context.update({
            "tenant_contract":      tenant_contract,
            "days_until_rent":      days_until_rent,
            "recent_payments":      recent_payments,
            "payments_made":        payments_made,
            "my_requests":          my_requests,
            "total_requests":       total_requests,
            "open_requests":        open_requests,
            "available_properties": available_properties,
        })

    return render(request, "users/dashboard.html", context)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("dashboard")
    else:
        form = CustomUserCreationForm()
    return render(request, "users/register.html", {"form": form})


# ---------------------------------------------------------------------------
# Other views
# ---------------------------------------------------------------------------

@login_required
def profile_view(request):
    if request.method == "POST":
        user = request.user
        user.first_name = request.POST.get("first_name", user.first_name)
        user.last_name  = request.POST.get("last_name",  user.last_name)
        user.email      = request.POST.get("email",      user.email)
        user.save()
        return redirect("profile")
    return render(request, "users/profile.html")


@login_required
def messages_view(request):
    return render(request, "users/messages.html")


@login_required
def community_view(request):
    return render(request, "community/feed.html")


@login_required
def maintenance_dashboard(request):
    user = request.user
    if user.role == "tenant":
        try:
            tenant_profile = user.profile
            requests = MaintenanceRequest.objects.filter(tenant=tenant_profile)
        except Exception:
            requests = MaintenanceRequest.objects.none()
    elif user.role == "landlord":
        requests = MaintenanceRequest.objects.filter(contract__landlord=user)
    else:
        requests = MaintenanceRequest.objects.filter(contract__agent=user)

    return render(request, "maintenance/dashboard.html", {"requests": requests})