from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model, login, update_session_auth_hash
from django.contrib import messages
from django.db.models import Sum, Case, When, IntegerField
from datetime import date
from calendar import month_abbr

from .forms import CustomUserCreationForm, ProfileForm, PasswordChangeForm
from maintenance.models import MaintenanceRequest
from notifications.models import Notification

User = get_user_model()




#yasser :

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
    from tenants.models import Tenant

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

    elif user.role == "tenant":
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

# walid :



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
# Profile view  — handles all tab POST actions via hidden `tab` field
# ---------------------------------------------------------------------------

#yasser

@login_required
def profile_view(request):
    user = request.user
    form = ProfileForm(instance=user)

    if request.method == "POST":
        tab = request.POST.get("tab", "personal")

        # ── Personal info ──────────────────────────────────────────────────
        if tab == "personal":
            form = ProfileForm(request.POST, instance=user)
            if form.is_valid():
                u = form.save(commit=False)
                u.first_name = request.POST.get("first_name", u.first_name).strip()
                u.last_name  = request.POST.get("last_name",  u.last_name).strip()
                role = request.POST.get("role")
                if role in ("landlord", "agent", "tenant"):
                    u.role = role
                u.save()
                messages.success(request, "Profile updated successfully.")
            else:
                messages.error(request, "Please correct the errors below.")
            return redirect("profile")

        # ── Security / password ────────────────────────────────────────────
        elif tab == "security":
            pw_form = PasswordChangeForm(user=user, data=request.POST)
            if pw_form.is_valid():
                pw_form.save()
                # Keep the user logged in after password change
                update_session_auth_hash(request, user)
                messages.success(request, "Password updated successfully.")
            else:
                for field, errors in pw_form.errors.items():
                    for err in errors:
                        messages.error(request, f"{field}: {err}")
            return redirect("profile")

        # ── Session revocation (placeholder — implement with your session model) ──
        elif tab in ("revoke_session", "revoke_all"):
            # TODO: flush specific or all non-current sessions
            messages.success(request, "Session(s) revoked.")
            return redirect("profile")

        # ── Notification preferences ───────────────────────────────────────
        elif tab == "notifications":
            prefs = {
                "email_payment":     "notif_email_payment"     in request.POST,
                "email_maintenance": "notif_email_maintenance"  in request.POST,
                "email_lease_expiry":"notif_email_lease_expiry" in request.POST,
                "email_overdue":     "notif_email_overdue"      in request.POST,
                "email_messages":    "notif_email_messages"     in request.POST,
                "push_urgent":       "notif_push_urgent"        in request.POST,
                "push_digest":       "notif_push_digest"        in request.POST,
                "push_updates":      "notif_push_updates"       in request.POST,
                "quiet_from":        request.POST.get("quiet_from", "22:00"),
                "quiet_until":       request.POST.get("quiet_until", "08:00"),
            }
            # Persist to user.notification_settings JSON field (or a separate model)
            if hasattr(user, "notification_settings"):
                user.notification_settings = prefs
                user.save(update_fields=["notification_settings"])
            messages.success(request, "Notification preferences saved.")
            return redirect("profile")

        # ── Avatar upload ──────────────────────────────────────────────────
        elif tab == "avatar":
            avatar_file = request.FILES.get("avatar")
            if avatar_file:
                if hasattr(user, "avatar"):
                    user.avatar.save(avatar_file.name, avatar_file, save=True)
                    messages.success(request, "Profile photo updated.")
                else:
                    messages.error(request, "Avatar uploads are not configured.")
            return redirect("profile")

    # ── GET ────────────────────────────────────────────────────────────────
    # Build role-aware stats for sidebar
    stats = _build_profile_stats(user)

    # Activity log — adapt to your own audit/log model
    activity_log = _build_activity_log(user)

    # Notification settings
    notif_settings = getattr(user, "notification_settings", {}) or {}

    context = {
        "form":            form,
        "stats":           stats,
        "activity_log":    activity_log,
        "notif_settings":  notif_settings,
    }
    return render(request, "users/profile.html", context)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_profile_stats(user):
    """Return sidebar stat counts keyed by role."""
    stats = {}
    try:
        if user.role == "landlord":
            from properties.models import Property
            from tenants.models import Tenant
            from contracts.models import Contract
            stats["properties_count"] = Property.objects.filter(owner=user).count()
            stats["tenants_count"]    = Contract.objects.filter(
                landlord=user, status="active"
            ).count()

        elif user.role == "agent":
            from properties.models import Property
            from contracts.models import Contract
            stats["listings_count"] = Property.objects.filter(agent=user).count()
            stats["clients_count"]  = Contract.objects.filter(
                agent=user, status="active"
            ).values("tenant").distinct().count()

        elif user.role == "tenant":
            from payments.models import Payment
            from tenants.models import Tenant
            tenant_profile = Tenant.objects.filter(user=user).first()
            if tenant_profile:
                stats["payments_count"] = Payment.objects.filter(
                    contract__tenant=tenant_profile, status="paid"
                ).count()
            else:
                stats["payments_count"] = 0
            stats["requests_count"] = MaintenanceRequest.objects.filter(tenant=user).count()
    except Exception:
        pass
    return stats


def _build_activity_log(user):
    """
    Build a list of activity dicts from your audit model.
    Each dict: { title, timestamp, category, device }
    Categories: 'login' | 'edit' | 'security' | 'danger'

    Replace the body below with a real query against your audit/log model,
    e.g. AuditLog.objects.filter(user=user).order_by('-timestamp')[:20]
    """
    # Placeholder — swap for real queryset:
    return []


# ---------------------------------------------------------------------------
# Delete account
# ---------------------------------------------------------------------------

@login_required
def delete_account_view(request):
    if request.method == "POST":
        user = request.user
        user.delete()
        messages.success(request, "Your account has been deleted.")
        return redirect("register")
    return redirect("profile")


# ---------------------------------------------------------------------------
# Other views
# ---------------------------------------------------------------------------

@login_required
def messages_view(request):
    return render(request, "users/messages.html")


@login_required
def community_view(request):
    return render(request, "community/feed.html")


#yasser :

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