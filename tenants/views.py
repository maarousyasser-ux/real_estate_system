from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from tenants.models import Tenant
from properties.models import Property
from contracts.models import Contract
from notifications.services import create_notification
from rentals.models import RentalRequest


@login_required
def tenant_list(request):
    tenants = Tenant.objects.select_related('user', 'property').all()
    return render(request, 'tenants/tenant_list.html', {'tenants': tenants})


@login_required
def tenant_lease(request):

    contract = (
        Contract.objects
        .select_related("tenant", "property", "tenant__user")
        .filter(tenant__user_id=request.user.id)
        .filter(status__iexact="active")
        .order_by("-id")
        .first()
    )

    print("DEBUG CONTRACT:", contract)

    return render(request, "leases/tenant_lease.html", {
        "tenant_contract": contract
    })

@login_required
def assign_tenant(request, property_id):
    property_obj = get_object_or_404(Property, id=property_id)

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        user_obj = get_object_or_404(Tenant._meta.get_field('user').related_model, id=user_id)

        tenant = Tenant.objects.create(
            user=user_obj,
            property=property_obj,
            phone_number=request.POST.get('phone', '0600000000'),
            emergency_contact=request.POST.get('emergency', 'Not Provided'),
            lease_start=request.POST.get('start_date'),
            lease_end=request.POST.get('end_date'),
            is_active=True
        )

        property_obj.status = 'occupied'
        property_obj.save()

        create_notification(
            user_obj,
            "Tenant Assigned",
            f"You were assigned to {property_obj.title}",
            type="tenant"
        )

        return redirect('property_detail', pk=property_id)


@login_required
def remove_tenant(request, tenant_id):
    tenant = get_object_or_404(Tenant, id=tenant_id)
    prop = tenant.property

    if prop:
        prop.status = 'available'
        prop.save()

    tenant.delete()
    return redirect('property_list')