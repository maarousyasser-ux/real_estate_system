from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from contracts.models import Contract
from .forms import (
    MaintenanceCommentForm,
    MaintenanceRequestForm,
    MaintenanceStatusForm
)
from .models import MaintenanceRequest


# =====================================================
# LIST VIEW
# =====================================================
@login_required
def request_list(request):

    is_staff = request.user.role in ['agent', 'landlord']

    if request.user.role == 'tenant':
        qs = MaintenanceRequest.objects.filter(tenant=request.user)

    elif request.user.role == 'landlord':
        qs = MaintenanceRequest.objects.filter(contract__landlord=request.user)

    elif request.user.role == 'agent':
        qs = MaintenanceRequest.objects.filter(contract__agent=request.user)

    else:
        qs = MaintenanceRequest.objects.none()

    # Filters
    status_filter = request.GET.get('status', '')
    priority_filter = request.GET.get('priority', '')
    category_filter = request.GET.get('category', '')
    search = request.GET.get('q', '')

    if status_filter:
        qs = qs.filter(status=status_filter)

    if priority_filter:
        qs = qs.filter(priority=priority_filter)

    if category_filter:
        qs = qs.filter(category=category_filter)

    if search:
        qs = qs.filter(title__icontains=search)

    page = Paginator(qs, 10).get_page(request.GET.get('page'))

    counts = {}

    if request.user.role == 'landlord':
        all_qs = MaintenanceRequest.objects.filter(contract__landlord=request.user)

        counts = {
            'total': all_qs.count(),
            'pending': all_qs.filter(status='pending').count(),
            'in_progress': all_qs.filter(status='in_progress').count(),
            'resolved': all_qs.filter(status='resolved').count(),
            'urgent': all_qs.filter(priority='urgent').count(),
        }

    return render(request, 'maintenance/request_list.html', {
        'page_obj': page,
        'is_staff': is_staff,
        'counts': counts,
        'status_choices': MaintenanceRequest.STATUS_CHOICES,
        'priority_choices': MaintenanceRequest.PRIORITY_CHOICES,
        'category_choices': MaintenanceRequest.CATEGORY_CHOICES,
        'current_status': status_filter,
        'current_priority': priority_filter,
        'current_category': category_filter,
        'search': search,
    })


# =====================================================
# CREATE REQUEST (FIXED)
# =====================================================
@login_required
def request_create(request):

    if request.user.role != 'tenant':
        messages.error(request, "Only tenants can create requests.")
        return redirect('maintenance:list')

    # 🔥 tenant MUST choose contract
    contracts = Contract.objects.filter(
        tenant__user=request.user,
        status='active'
    ).select_related('property', 'landlord')

    if not contracts.exists():
        messages.error(request, "You are not renting any property.")
        return redirect('maintenance:list')

    if request.method == 'POST':

        form = MaintenanceRequestForm(request.POST, request.FILES)

        if form.is_valid():

            contract_id = request.POST.get('contract')

            contract = get_object_or_404(
                Contract,
                id=contract_id,
                tenant__user=request.user,
                status='active'
            )

            req = form.save(commit=False)

            req.tenant = request.user
            req.contract = contract

            req.property_address = contract.property.address
            req.unit_number = getattr(contract, 'unit_number', '')

            req.save()

            messages.success(request, "Request submitted successfully.")

            return redirect('maintenance:detail', pk=req.pk)

    else:
        form = MaintenanceRequestForm()

    return render(request, 'maintenance/request_form.html', {
        'form': form,
        'title': 'New Maintenance Request',
        'contracts': contracts,
    })


# =====================================================
# DETAIL VIEW (CORRECT OWNERSHIP LOGIC)
# =====================================================
@login_required
def request_detail(request, pk):

    req = get_object_or_404(
        MaintenanceRequest.objects.select_related('contract'),
        pk=pk
    )

    allowed = (
        req.tenant == request.user or
        (req.contract and req.contract.landlord == request.user) or
        (req.contract and req.contract.agent == request.user)
    )

    if not allowed:
        messages.error(request, "Access denied.")
        return redirect('maintenance:list')

    is_staff = request.user.role in ['agent', 'landlord']

    comments = (
        req.comments.all()
        if is_staff
        else req.comments.filter(is_internal=False)
    )

    comment_form = MaintenanceCommentForm()
    status_form = MaintenanceStatusForm(instance=req) if is_staff else None

    if request.method == 'POST':

        action = request.POST.get('action')

        if action == 'comment':

            form = MaintenanceCommentForm(request.POST)

            if form.is_valid():
                comment = form.save(commit=False)
                comment.request = req
                comment.author = request.user

                if not is_staff:
                    comment.is_internal = False

                comment.save()

                messages.success(request, "Comment added.")
                return redirect('maintenance:detail', pk=pk)

        elif action == 'update_status' and is_staff:

            form = MaintenanceStatusForm(request.POST, instance=req)

            if form.is_valid():
                form.save()
                messages.success(request, "Request updated.")
                return redirect('maintenance:detail', pk=pk)

    return render(request, 'maintenance/request_detail.html', {
        'req': req,
        'comments': comments,
        'comment_form': comment_form,
        'status_form': status_form,
        'is_staff': is_staff,
    })


# =====================================================
# EDIT + CLOSE (UNCHANGED LOGIC BUT SAFE)
# =====================================================
@login_required
def request_edit(request, pk):

    req = get_object_or_404(
        MaintenanceRequest,
        pk=pk,
        tenant=request.user
    )

    if req.status != 'pending':
        messages.warning(request, "Only pending requests can be edited.")
        return redirect('maintenance:detail', pk=pk)

    form = MaintenanceRequestForm(request.POST or None, request.FILES or None, instance=req)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Updated successfully.")
        return redirect('maintenance:detail', pk=pk)

    return render(request, 'maintenance/request_form.html', {
        'form': form,
        'title': 'Edit Request',
        'req': req,
    })


@login_required
def request_close(request, pk):

    req = get_object_or_404(
        MaintenanceRequest,
        pk=pk,
        tenant=request.user
    )

    if req.status == 'resolved':
        req.status = 'closed'
        req.save()
        messages.success(request, "Request closed.")

    return redirect('maintenance:list')