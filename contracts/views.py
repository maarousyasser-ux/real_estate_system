from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Contract
from properties.models import Property
from tenants.models import Tenant
from .forms import ContractForm
from notifications.services import create_notification

from rentals.models import RentalRequest


# =====================================================
# LIST
# =====================================================
@login_required
def contract_list(request):

    user = request.user

    qs = Contract.objects.select_related("property", "tenant__user", "agent")

    if user.role == "landlord":
        contracts = qs.all()

    elif user.role == "agent":
        contracts = qs.filter(agent=user)

    elif user.role == "tenant":
        contracts = qs.filter(tenant__user=user)

    else:
        contracts = Contract.objects.none()

    return render(request, "contracts/contract_list.html", {
        "contracts": contracts,
        "total": contracts.count(),
        "active": contracts.filter(status="active").count(),
        "pending": contracts.filter(status="pending").count(),
        "cancelled": contracts.filter(status="cancelled").count(),
    })


# =====================================================
# DETAIL
# =====================================================
@login_required
def contract_detail(request, pk):

    contract = get_object_or_404(Contract, pk=pk)

    user = request.user

    allowed = (
        user.role == "landlord"
        or contract.agent == user
        or contract.tenant.user == user
    )

    if not allowed:
        return redirect("dashboard")

    return render(request, "contracts/contract_detail.html", {
        "contract": contract,
        "can_approve": (
            user == contract.tenant.user and contract.status == "pending"
        )
    })
# =====================================================
# CREATE CONTRACT (FROM RENTAL APPROVAL)
# =====================================================
@login_required
def contract_create(request):

    tenant_id = request.GET.get("tenant")
    property_id = request.GET.get("property")

    # ✅ SAFE FETCH
    tenant = get_object_or_404(Tenant, id=tenant_id)
    property_obj = get_object_or_404(Property, id=property_id)

    if request.method == "POST":

        form = ContractForm(request.POST)

        if form.is_valid():

            contract = form.save(commit=False)

            # 🔥 FORCE RELATIONS (IMPORTANT SECURITY FIX)
            contract.tenant = tenant
            contract.property = property_obj

            # assign creator role
            if request.user.role == "agent":
                contract.agent = request.user
            elif request.user.role == "landlord":
                contract.landlord = request.user

            # default state → waiting tenant approval
            contract.status = "pending"
            contract.save()

            messages.success(request, "Contract sent to tenant for approval.")
            return redirect("contract_detail", pk=contract.pk)

    else:
        form = ContractForm()

    return render(request, "contracts/contract_create.html", {
        "form": form,
        "tenant": tenant,
        "property": property_obj,
    })
# =====================================================
# APPROVE CONTRACT (TENANT ONLY)
# =====================================================
@login_required
def contract_approve(request, pk):

    contract = get_object_or_404(Contract, pk=pk)

    # only tenant can approve
    if request.user != contract.tenant.user:
        return redirect("dashboard")

    # activate contract
    contract.status = "active"
    contract.save()

    # update property
    contract.property.status = "occupied"
    contract.property.save()

    # generate payments AFTER approval
    contract.generate_payments()

    return redirect("contract_detail", pk=pk)
# =====================================================
# DECLINE CONTRACT (TENANT ONLY)
# =====================================================
@login_required
def contract_decline(request, pk):

    contract = get_object_or_404(Contract, pk=pk)

    if request.user != contract.tenant.user:
        return redirect("dashboard")

    contract.status = "cancelled"
    contract.save()

    # free property again
    contract.property.status = "available"
    contract.property.save()

    return redirect("contract_list")


# =====================================================
# TERMINATE CONTRACT (LANDLORD / AGENT)
# =====================================================
@login_required
def contract_terminate(request, pk):

    contract = get_object_or_404(Contract, pk=pk)

    if request.user.role not in ["agent", "landlord"]:
        return redirect("dashboard")

    if request.method == "POST":

        contract.status = "cancelled"
        contract.save()

        contract.property.status = "available"
        contract.property.save()

        tenant = contract.tenant
        tenant.property = None
        tenant.is_active = False
        tenant.save()

        create_notification(
            contract.tenant.user,
            "Contract Terminated",
            f"Your lease for {contract.property.title} ended",
            type="contract"
        )

        messages.success(request, "Contract terminated.")
        return redirect("contract_list")

    return render(request, "contracts/confirm_terminate.html", {
        "contract": contract
    })