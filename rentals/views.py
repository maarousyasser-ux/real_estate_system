from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import RentalRequest
from tenants.models import Tenant
from properties.models import Property


# =====================================================
# LIST REQUESTS
# =====================================================
@login_required
def rental_requests(request):

    user = request.user

    # TENANT → only sees own requests + status
    if user.role == "tenant":
        requests = RentalRequest.objects.filter(tenant=user)
        return render(request, "users/dashboard.html", {
            "requests": requests
        })

    # AGENT / LANDLORD → see property requests
    elif user.role == "agent":
        requests = RentalRequest.objects.filter(property__agent=user)

    elif user.role == "landlord":
        requests = RentalRequest.objects.filter(property__owner=user)

    else:
        requests = RentalRequest.objects.none()

    return render(request, "rentals/requests.html", {
        "requests": requests
    })


# =====================================================
# CREATE REQUEST (TENANT)
# =====================================================
@login_required
def request_rent(request, property_id):

    prop = get_object_or_404(Property, id=property_id)

    # prevent duplicates
    obj, created = RentalRequest.objects.get_or_create(
        tenant=request.user,
        property=prop,
        defaults={'status': 'pending'}
    )

    if created:
        messages.success(request, "Request sent successfully!")
    else:
        messages.info(request, "You already sent a request.")

    return redirect("rentals:rental_requests")


# =====================================================
# APPROVE REQUEST (LANDLORD / AGENT ONLY)
# =====================================================
@login_required
def approve_request(request, pk):

    req = get_object_or_404(RentalRequest, pk=pk)

    # security
    if request.user not in [req.property.owner, req.property.agent]:
        return redirect("dashboard")

    if request.method == "POST":

        # 🔥 redirect to contract creation WITH request info
        return redirect(
            f"/contracts/create/?tenant={req.tenant.tenant.id}&property={req.property.id}&request={req.id}"
        )


# =====================================================
# REJECT REQUEST (DELETE)
# =====================================================
@login_required
def reject_request(request, pk):

    req = get_object_or_404(RentalRequest, pk=pk)

    if request.user not in [req.property.owner, req.property.agent]:
        return redirect("dashboard")

    if request.method == "POST":
        req.delete()  # 🔥 remove request immediately
        messages.warning(request, "Request rejected.")

    return redirect("rentals:rental_requests")