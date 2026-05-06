from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from .models import Payment
from contracts.models import Contract

from notifications.services import create_notification


@login_required
def payment_list(request):

    user = request.user

    payments = Payment.objects.select_related(
        'contract__tenant__user',
        'contract__property'
    )

    if user.role == 'landlord':
        payments = payments.all()

    elif user.role == 'agent':
        payments = payments.filter(contract__agent=user)

    elif user.role == 'tenant':
        payments = payments.filter(contract__tenant__user=user)

    else:
        payments = Payment.objects.none()

    payments = payments.order_by("-due_date")

    total_due = sum(p.amount for p in payments if p.status in ['pending', 'overdue'])
    total_paid = sum(p.amount for p in payments if p.status == 'paid')
    overdue = payments.filter(status='overdue').count()

    return render(request, 'payments/payment_list.html', {
        'payments': payments,
        'total_due': total_due,
        'total_paid': total_paid,
        'overdue': overdue,
    })
@login_required
def mark_paid(request, pk):

    payment = get_object_or_404(Payment, pk=pk)
    user = request.user

    # SECURITY RULE
    allowed = (
        user.role == "landlord"
        or (user.role == "agent" and payment.contract.agent == user)
        or (user.role == "tenant" and payment.contract.tenant.user == user)
    )

    if not allowed:
        messages.error(request, "Not allowed.")
        return redirect('payment_list')

    if request.method == 'POST':
        payment.status = 'paid'
        payment.paid_date = timezone.now().date()
        payment.save(update_fields=['status', 'paid_date'])

        messages.success(request, f"{payment.month} marked as paid.")
        
        
        
        create_notification(
    payment.contract.tenant.user,
    "Payment Received",
    f"Your rent for {payment.month} has been marked as paid.",
    type="payment"
)

    return redirect('payment_list')
@login_required
def payment_detail(request, pk):

    payment = get_object_or_404(Payment, pk=pk)
    user = request.user

    allowed = (
        user.role == "landlord"
        or (payment.contract.agent == user)
        or (user.role == "tenant" and payment.contract.tenant.user == user)
    )

    if not allowed:
        return redirect('dashboard')

    return render(request, 'payments/payment_detail.html', {
        'payment': payment
    })
    
    
    
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required

from .models import Payment


@login_required
def process_payment(request, pk):
    payment = get_object_or_404(Payment, pk=pk)

    # only tenant can pay
    if request.user.role != "tenant":
        return redirect("payment_list")

    # extra safety: must be owner
    if payment.contract.tenant.user != request.user:
        return redirect("payment_list")

    payment.status = "paid"
    payment.save()

    return redirect("payment_list")