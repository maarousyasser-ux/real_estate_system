from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Contract
from properties.models import Property
from tenants.models import Tenant

from notifications.services import create_notification
from .forms import ContractForm

# ─────────────────────────────
# LIST
# ─────────────────────────────
@login_required
@login_required
def contract_list(request):
    user = request.user

    base_qs = Contract.objects.select_related(
        "property", "tenant__user", "agent"
    )

    if user.role == "landlord":
        contracts = base_qs.all()

    elif user.role == "agent":
        contracts = base_qs.filter(agent=user)

    elif user.role == "tenant":
        contracts = base_qs.filter(tenant__user=user)

    else:
        contracts = Contract.objects.none()

    return render(request, "contracts/contract_list.html", {
        "contracts": contracts,
        "total": contracts.count(),
        "active": contracts.filter(status="active").count(),
        "expired": contracts.filter(status="expired").count(),
        "expiring": sum(
            1 for c in contracts if c.status == "active" and c.is_expiring_soon()
        ),
        "user_role": user.role,
    })
# ─────────────────────────────
# DETAIL
# ─────────────────────────────
@login_required
def contract_detail(request, pk):
    contract = get_object_or_404(Contract, pk=pk)
    user = request.user

    allowed = (
        user.role == "landlord"
        or contract.agent == user
        or (user.role == "tenant" and contract.tenant.user == user)
    )

    if not allowed:
        return redirect("dashboard")

    return render(request, "contracts/contract_detail.html", {
        "contract": contract,
        "user_role": user.role,
        "is_tenant_owner": user.role == "tenant" and contract.tenant.user == user
    })



# ─────────────────────────────
# CREATE CONTRACT (FIXED + CLEAN)
# ─────────────────────────────
from .forms import ContractForm
@login_required
def contract_create(request):
    tenant_id = request.GET.get("tenant")
    property_id = request.GET.get("property")

    if request.method == "POST":
        form = ContractForm(request.POST)

        if form.is_valid():
            contract = form.save(commit=False)

            # ✅ FORCE values from URL (important)
            contract.tenant_id = tenant_id
            contract.property_id = property_id

            if request.user.role == "agent":
                contract.agent = request.user
            elif request.user.role == "landlord":
                contract.landlord = request.user

            contract.status = "pending"
            contract.save()

            return redirect("contract_detail", pk=contract.pk)

        else:
            print("FORM ERRORS:", form.errors)  # 👈 keep this

    else:
        form = ContractForm()

    return render(request, "contracts/contract_create.html", {
        "form": form,
        "tenant_id": tenant_id,
        "property_id": property_id,
    })
# TERMINATE CONTRACT (FIXED + NOTIFICATIONS)
# ─────────────────────────────
@login_required
def contract_terminate(request, pk):
    contract = get_object_or_404(Contract, pk=pk)
    user = request.user

    if user.role not in ["agent", "landlord"]:
        return redirect("dashboard")

    if request.method == "POST":

        contract.status = "cancelled"
        contract.save()

        property_obj = contract.property
        property_obj.status = "available"
        property_obj.save()

        tenant = contract.tenant
        tenant.property = None
        tenant.is_active = False
        tenant.save()

        # ───── NOTIFICATIONS ─────

        create_notification(
            contract.tenant.user,
            "Contract Terminated",
            f"Your lease for {property_obj.title} has been ended",
            type="contract"
        )

        if contract.agent:
            create_notification(
                contract.agent,
                "Contract Closed",
                f"Contract for {property_obj.title} was terminated",
                type="contract"
            )

        if contract.landlord:
            create_notification(
                contract.landlord,
                "Tenant Left",
                f"{property_obj.title} is now available",
                type="contract"
            )

        messages.success(request, "Contract terminated successfully.")
        return redirect("contract_list")

    return render(request, "contracts/confirm_terminate.html", {
        "contract": contract
    })
    
    
    
    
    
    
    
    
    
    
    
@login_required
def contract_approve(request, pk):
    contract = get_object_or_404(Contract, pk=pk)

    if request.user != contract.tenant.user:
        return redirect("dashboard")

    contract.status = "active"
    contract.save()

    # update property
    contract.property.status = "occupied"
    contract.property.save()

    # notify landlord
    from notifications.services import create_notification
    if contract.landlord:
        create_notification(
            contract.landlord,
            "Contract Approved",
            f"{contract.tenant.user.username} approved the contract",
            type="contract"
        )

    return redirect("contract_detail", pk=pk)










@login_required
def contract_approve(request, pk):
    contract = get_object_or_404(Contract, pk=pk)

    if request.user != contract.tenant.user:
        return redirect("dashboard")

    # 1. activate contract
    contract.status = "active"
    contract.save()

    # 2. update property
    contract.property.status = "occupied"
    contract.property.save()

    contract.generate_payments()

    return redirect("contract_detail", pk=pk)


@login_required
def contract_decline(request, pk):
    contract = get_object_or_404(Contract, pk=pk)

    if request.user != contract.tenant.user:
        return redirect("dashboard")

    contract.status = "cancelled"
    contract.save()

    return redirect("contract_detail", pk=pk)










