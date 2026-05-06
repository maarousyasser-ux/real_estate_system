from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied

from .models import Property
from .forms import PropertyForm


from notifications.models import Notification

def get_user_notifications(user):
    return Notification.objects.filter(user=user).order_by("-created_at")


# ========================
# PROPERTY LIST
# ========================
@login_required
def property_list(request):
    user = request.user
    
    if user.role == 'landlord':
        properties = Property.objects.filter(owner=user)
    elif user.role == 'agent':
        properties = Property.objects.filter(agent=user)
    else:
        # Tenants only see confirmed and available listings
        properties = Property.objects.filter(is_confirmed=True, status='available')

    # Add a search filter logic
    query = request.GET.get('search')
    if query:
        properties = properties.filter(title__icontains=query)

    return render(request, 'properties/property_list.html', {
        'properties': properties.order_by('-created_at'),
        'total_value': sum(p.price for p in properties) # Logic: Show portfolio value
    })
# ========================
# PROPERTY DETAIL
# ========================
@login_required
def property_detail(request, pk):
    property_instance = get_object_or_404(
        Property.objects.prefetch_related('tenants__user'),
        pk=pk
    )

    if request.user.role == 'landlord' and property_instance.owner != request.user:
        raise PermissionDenied
    if request.user.role == 'agent' and property_instance.agent != request.user:
        raise PermissionDenied

    return render(request, 'properties/property_detail.html', {
        'property': property_instance
    })


# ========================
# CREATE PROPERTY
# ========================
@login_required
def property_create(request):
    if request.method == 'POST':
        form = PropertyForm(request.POST, request.FILES, user=request.user)

        if form.is_valid():
            property_instance = form.save(commit=False)

            if request.user.role == 'agent':
                property_instance.agent = request.user
                property_instance.is_confirmed = False
                messages.info(request, "Property created. Waiting for landlord confirmation.")
            else:
                property_instance.owner = request.user
                property_instance.is_confirmed = True

            property_instance.save()
            return redirect('property_list')
    else:
        form = PropertyForm(user=request.user)

    return render(request, 'properties/property_form.html', {'form': form})


# ========================
# EDIT PROPERTY
# ========================
@login_required
def property_edit(request, pk):
    property_instance = get_object_or_404(Property, pk=pk)

    # STRICT SECURITY: Only the specific owner or specific agent can access
    if request.user != property_instance.owner and request.user != property_instance.agent:
        raise PermissionDenied

    if request.method == 'POST':
        form = PropertyForm(request.POST, request.FILES, instance=property_instance, user=request.user)
        if form.is_valid():
            # Logic: Prevent an agent from changing the owner during an edit
            if request.user.role == 'agent':
                property_instance.owner = property_instance.owner # Keep original owner
            
            form.save()
            messages.success(request, "Listing updated successfully.")
            return redirect('property_list')
    else:
        form = PropertyForm(instance=property_instance, user=request.user)

    return render(request, 'properties/property_form.html', {'form': form, 'property': property_instance})

# ========================
# CONFIRM PROPERTY
# ========================
@login_required
def confirm_property(request, pk):
    property_instance = get_object_or_404(Property, pk=pk)

    if request.user != property_instance.owner:
        raise PermissionDenied

    property_instance.is_confirmed = True
    property_instance.save()

    messages.success(request, f"Property '{property_instance.title}' has been confirmed.")
    return redirect('property_list')


# ========================
# CHANGE STATUS
# ========================
@login_required
def change_status(request, pk):
    if request.method == 'POST':
        property_instance = get_object_or_404(Property, pk=pk)

        if property_instance.owner != request.user and property_instance.agent != request.user:
            raise PermissionDenied

        new_status = request.POST.get('status')

        if new_status in dict(Property.STATUS_CHOICES):
            property_instance.status = new_status
            property_instance.save()

    return redirect('property_list')







def public_property_list(request):

    properties = Property.objects.filter(is_confirmed=True, status='available')
    

    query = request.GET.get('search')
    if query:
        properties = properties.filter(title__icontains=query)
        
    return render(request, 'properties/public_list.html', {'properties': properties})







@login_required
@login_required
def dashboard(request):
    user = request.user
    context = {}

    if user.role == 'tenant':
        # LOGIC: Get all properties available in the system for the "Marketplace"
        context['available_properties'] = Property.objects.filter(
            is_confirmed=True, 
            status='available'
        ).order_by('-created_at')

        # Logic for the tenant's current specific lease (if they have one)
        context['current_lease'] = Property.objects.filter(tenants__user=user).first()
        
    elif user.role == 'landlord':
        context['properties'] = Property.objects.filter(owner=user)
        # ... (rest of your landlord logic)

    return render(request, 'dashboard.html', context)











@login_required
def submit_maintenance_request(request):
    if request.method == 'POST':
        category = request.POST.get('category')
        description = request.POST.get('description')
        # Logic to save to your Maintenance model goes here
        return redirect('dashboard') # Redirect back to dashboard