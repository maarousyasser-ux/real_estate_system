from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Tenant
from properties.models import Property
from django.contrib.auth import get_user_model

from django.db import IntegrityError
from contracts.models import Contract

from notifications.models import Notification

def get_user_notifications(user):
    return Notification.objects.filter(user=user).order_by("-created_at")

# Get the custom user model (users_user table)
User = get_user_model()

@login_required
def tenant_list(request):
    """
    Displays all tenants. Uses select_related to join tables in one SQL query
    for better performance with large datasets.
    """
    tenants = Tenant.objects.select_related('user', 'property').all()
    return render(request, 'tenants/tenant_list.html', {'tenants': tenants})

from notifications.services import create_notification

@login_required
def assign_tenant(request, property_id):
    property_obj = get_object_or_404(Property, id=property_id)

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        user_obj = get_object_or_404(User, id=user_id)

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

        # ✅ CREATE NOTIFICATION HERE
        create_notification(
            user_obj,
            "Tenant Assigned",
            f"You were assigned to {property_obj.title}",
            type="tenant"
        )

        return redirect('property_detail', pk=property_id)

@login_required
def remove_tenant(request, tenant_id):
    """
    Optional helper: Unassigns a tenant and makes the property available again.
    """
    tenant = get_object_or_404(Tenant, id=tenant_id)
    prop = tenant.property
    
    if prop:
        prop.status = 'available'
        prop.save()
        
    tenant.delete() # Or set property to NULL if you want to keep the tenant history
    return redirect('property_list')








@login_required
def tenant_lease(request):
    contract = Contract.objects.filter(
        tenant__user=request.user,
        status="active"
    ).select_related("property").first()

    return render(request, "leases/tenant_lease.html", {
        "tenant_contract": contract
    })