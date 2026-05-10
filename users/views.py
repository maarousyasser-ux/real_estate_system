from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model, login
from django.db.models import Sum, Case, When, IntegerField
from datetime import date
from calendar import month_abbr

from .forms import CustomUserCreationForm
from maintenance.models import MaintenanceRequest
from notifications.models import Notification

User = get_user_model()


# ---------------------------------------------------------------------------
# Month helpers
# ---------------------------------------------------------------------------

def _last_6_months():
    today = date.today()
    result = []
    for i in range(5, -1, -1):
        month = (today.month - i - 1) % 12 + 1
        year  = today.year + ((today.month - i - 1) // 12)
        result.append((year, month, month_abbr[month]))
    return result


def _monthly_sum(qs, date_field, amount_field, months):
    out = []
    for year, month, _ in months:
        total = qs.filter(
            **{f"{date_field}__year": year, f"{date_field}__month": month}
        ).aggregate(s=Sum(amount_field))["s"] or 0
        out.append(float(total))
    return out


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@login_required
def dashboard_view(request):
    user    = request.user
    context = {
        "unread_count": Notification.objects.filter(user=user, is_read=False).count()
    }

    from contracts.models import Contract
    from payments.models import Payment
    from properties.models import Property
    from tenants.models import Tenant  # Tenant profile model

    # Contract.tenant  → Tenant model (profile, has .user FK to User)
    # Contract.landlord → User directly
    # Contract.agent    → User directly
    # Property.owner    → User directly
    # Property.agent    → User directly
    # MaintenanceRequest.tenant → User directly

    # -------------------------------------------------------------------------
    # LANDLORD
    # -------------------------------------------------------------------------
    if user.role == "landlord":
        properties   = Property.objects.filter(owner=user)
        contracts    = Contract.objects.filter(landlord=user, status="active")
        all_payments = Payment.objects.filter(contract__landlord=user)

        total_revenue   = all_payments.filter(status="paid").aggregate(s=Sum("amount"))["s"] or 0
        active_tenants  = contracts.count()
        total_units     = properties.count()
        occupied_units  = properties.filter(status="occupied").count()
        available_units = properties.filter(status="available").count()
        occupancy_pct   = round(occupied_units / total_units * 100) if total_units else 0

        maintenance_qs      = MaintenanceRequest.objects.filter(contract__landlord=user)
        pending_maintenance = maintenance_qs.filter(status__in=["pending", "in_progress"]).count()

        months       = _last_6_months()
        chart_labels = [lbl for _, _, lbl in months]
        revenue_data = _monthly_sum(all_payments.filter(status="paid"), "paid_date", "amount", months)
        expense_data = [0] * 6

        recent_payments = (
            Payment.objects.filter(contract__landlord=user)
            .select_related("contract__tenant", "contract__property")
            .order_by("-due_date")[:8]
        )
        requests = (
            maintenance_qs
            .select_related("contract", "tenant")
            .order_by("-created_at")[:8]
        )

        context.update({
            "total_revenue":       total_revenue,
            "active_tenants":      active_tenants,
            "total_units":         total_units,
            "occupied_units":      occupied_units,
            "available_units":     available_units,
            "occupancy_pct":       occupancy_pct,
            "pending_maintenance": pending_maintenance,
            "maintenance_cost":    0,
            "chart_labels":        chart_labels,
            "revenue_data":        revenue_data,
            "expense_data":        expense_data,
            "recent_payments":     recent_payments,
            "requests":            requests,
        })

    # -------------------------------------------------------------------------
    # AGENT
    # -------------------------------------------------------------------------
    elif user.role == "agent":
        listings        = Property.objects.filter(agent=user)
        agent_contracts = Contract.objects.filter(agent=user)

        active_listings  = listings.filter(status="available").count()
        active_contracts = agent_contracts.filter(status="active").count()
        client_count     = (
            agent_contracts.filter(status="active")
            .values("tenant").distinct().count()
        )

        today = date.today()
        paid_this_month = (
            Payment.objects.filter(
                contract__agent=user,
                status="paid",
                paid_date__year=today.year,
                paid_date__month=today.month,
            ).aggregate(s=Sum("amount"))["s"] or 0
        )
        monthly_commission = round(float(paid_this_month) * 0.05, 2)

        months          = _last_6_months()
        chart_labels    = [lbl for _, _, lbl in months]
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

        pipeline = (
            agent_contracts.filter(status__in=["active", "pending"])
            .select_related("property", "tenant")
            .order_by("-signed_at")[:6]
        )
        listings_table   = listings.order_by("-id")[:8]
        recent_contracts = (
            agent_contracts
            .select_related("tenant", "property")
            .order_by("-signed_at")[:6]
        )

        context.update({
            "active_listings":    active_listings,
            "active_contracts":   active_contracts,
            "client_count":       client_count,
            "monthly_commission": monthly_commission,
            "chart_labels":       chart_labels,
            "commission_data":    commission_data,
            "pipeline":           pipeline,
            "listings_table":     listings_table,
            "recent_contracts":   recent_contracts,
        })

    # -------------------------------------------------------------------------
    # TENANT
    # -------------------------------------------------------------------------
    elif user.role == "tenant":
        # Contract.tenant is a FK to the Tenant model (not User directly).
        # The Tenant model has a `user` OneToOne/FK back to User.
        tenant_profile = Tenant.objects.filter(user=user).first()

        tenant_contract = None
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

        # Attach computed lease progress
        if tenant_contract:
            today = date.today()
            start, end = tenant_contract.start_date, tenant_contract.end_date
            if start and end and end > start:
                total_days     = (end - start).days
                elapsed        = max(0, (today - start).days)
                lease_pct      = min(100, round(elapsed / total_days * 100))
                days_remaining = max(0, (end - today).days)
            else:
                lease_pct = days_remaining = 0
            tenant_contract.lease_progress_pct = lease_pct
            tenant_contract.days_remaining      = days_remaining

        # Days until next rent payment
        days_until_rent = None
        if tenant_contract and tenant_contract.status == "active":
            nxt = (
                Payment.objects.filter(
                    contract=tenant_contract,
                    status__in=["pending", "overdue"],
                )
                .order_by("due_date")
                .first()
            )
            if nxt:
                days_until_rent = (nxt.due_date - date.today()).days

        # Payments — filter via Tenant profile through contract
        if tenant_profile:
            recent_payments = (
                Payment.objects.filter(contract__tenant=tenant_profile)
                .order_by("-due_date")[:6]
            )
            payments_made = (
                Payment.objects.filter(contract__tenant=tenant_profile, status="paid").count()
            )
        else:
            recent_payments = Payment.objects.none()
            payments_made   = 0

        # Maintenance — MaintenanceRequest.tenant is direct FK to User
        my_requests = (
            MaintenanceRequest.objects.filter(tenant=user)
            .order_by("-created_at")[:5]
        )
        total_requests = MaintenanceRequest.objects.filter(tenant=user).count()
        open_requests  = MaintenanceRequest.objects.filter(
            tenant=user, status__in=["pending", "in_progress"]
        ).count()

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
        u = request.user
        u.first_name = request.POST.get("first_name", u.first_name)
        u.last_name  = request.POST.get("last_name",  u.last_name)
        u.email      = request.POST.get("email",      u.email)
        u.save()
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
     
        qs = MaintenanceRequest.objects.filter(tenant=user)
    elif user.role == "landlord":
        qs = MaintenanceRequest.objects.filter(contract__landlord=user)
    else:
        qs = MaintenanceRequest.objects.filter(contract__agent=user)
    return render(request, "maintenance/dashboard.html", {"requests": qs})