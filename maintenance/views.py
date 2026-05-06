from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from .models import MaintenanceRequest
from contracts.models import Contract
from notifications.services import create_notification


# LIST
@login_required
def maintenance_list(request):

    user = request.user

    if user.role == "tenant":
        requests = MaintenanceRequest.objects.filter(created_by=user)

    elif user.role == "agent":
        requests = MaintenanceRequest.objects.filter(contract__agent=user)

    elif user.role == "landlord":
        requests = MaintenanceRequest.objects.filter(contract__landlord=user)

    else:
        requests = MaintenanceRequest.objects.none()

    return render(request, "maintenance/maintenance_list.html", {
        "requests": requests
    })


# CREATE (TENANT ONLY)
@login_required
def create_request(request):

    if request.user.role != "tenant":
        return redirect("dashboard")

    contract = Contract.objects.filter(
        tenant__user=request.user,
        status="active"
    ).select_related("property", "agent", "landlord").first()

    if not contract:
        return redirect("dashboard")

    if request.method == "POST":

        req = MaintenanceRequest.objects.create(
            contract=contract,
            title=request.POST.get("title"),
            description=request.POST.get("description"),
            priority=request.POST.get("priority", "medium"),
            created_by=request.user
        )

        # ─────────────────────────────
        # NOTIFICATIONS (FIXED)
        # ─────────────────────────────

        # Notify agent
        if contract.agent:
            create_notification(
                contract.agent,
                "New Maintenance Request",
                f"{req.title} in {contract.property.title}",
                type="maintenance"
            )

        # Notify landlord
        if contract.landlord:
            create_notification(
                contract.landlord,
                "New Maintenance Request",
                f"{req.title} submitted for {contract.property.title}",
                type="maintenance"
            )

        # Confirm to tenant
        create_notification(
            request.user,
            "Request Submitted",
            "Your maintenance request has been sent successfully.",
            type="maintenance"
        )

        return redirect("maintenance_list")

    return render(request, "maintenance/maintenance_create.html")

# UPDATE STATUS (AGENT / LANDLORD)
@login_required
def update_status(request, pk):

    req = get_object_or_404(MaintenanceRequest, pk=pk)

    if request.user.role not in ["agent", "landlord"]:
        return redirect("dashboard")

    if request.method == "POST":

        status = request.POST.get("status")
        req.status = status

        if status == "resolved":
            req.resolved_at = timezone.now()

        req.save()

    return redirect("maintenance_list")











def maintenance_detail(request, pk):
    req = get_object_or_404(MaintenanceRequest, pk=pk)

    return render(request, "maintenance/maintenance_detail.html", {
        "request_obj": req
    })