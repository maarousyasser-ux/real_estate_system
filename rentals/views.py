from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import RentalRequest
from tenants.models import Tenant
from properties.models import Property  # Ensure this import works

@login_required
def rental_requests(request):
    user = request.user

    # 👤 TENANT → go to dashboard
    if user.role == "tenant":
        requests = RentalRequest.objects.filter(tenant=user)

        return render(request, "users/dashboard.html", {
            "requests": requests
        })

    # 🧑‍💼 AGENT / 🏠 LANDLORD → request page
    elif user.role == "agent":
        requests = RentalRequest.objects.filter(property__agent=user)

    elif user.role == "landlord":
        requests = RentalRequest.objects.filter(property__owner=user)

    else:
        requests = RentalRequest.objects.none()

    return render(request, "rentals/requests.html", {
        "requests": requests
    })

@login_required
def request_rent(request, property_id):
    """View to handle the initial rental request from a tenant"""
    prop = get_object_or_404(Property, id=property_id)
    
    # Logic to prevent duplicate requests
    obj, created = RentalRequest.objects.get_or_create(
        tenant=request.user,
        property=prop,
        defaults={'status': 'pending'}
    )
    
    if created:
        messages.success(request, "Rental request sent successfully!")
    else:
        messages.info(request, "You have already sent a request for this property.")
        
    return redirect("rentals:rental_requests")

@login_required
def approve_request(request, pk):
    req = get_object_or_404(RentalRequest, pk=pk)

    # Security check
    if request.user != req.property.owner and request.user != req.property.agent:
        return redirect("dashboard")

    req.status = "approved"
    req.save()

    # Create tenant profile
    tenant, created = Tenant.objects.get_or_create(
        user=req.tenant,
        defaults={
            "emergency_contact": "Not provided",
            "is_active": True
        }
    )

    return redirect(f"/contracts/create/?tenant={tenant.id}&property={req.property.id}")

@login_required
def reject_request(request, pk):
    req = get_object_or_404(RentalRequest, pk=pk)

    if request.user != req.property.owner and request.user != req.property.agent:
        return redirect("dashboard")

    req.status = "rejected"
    req.save()
    messages.warning(request, "Request rejected.")
    return redirect("rentals:rental_requests")