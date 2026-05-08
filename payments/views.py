from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from .models import Payment
from notifications.services import create_notification


# =====================================================
# PAYMENT LIST (FULLY FIXED SECURITY)
# =====================================================
@login_required
def payment_list(request):

    user = request.user

    payments = Payment.objects.select_related(
        'contract__tenant__user',
        'contract__property',
        'contract__landlord',
        'contract__agent'
    )

    # =====================================================
    # ROLE FILTERING (NO DATA LEAKS)
    # =====================================================
    if user.role == "tenant":
        payments = payments.filter(contract__tenant__user=user)

    elif user.role == "agent":
        payments = payments.filter(contract__agent=user)

    elif user.role == "landlord":
        payments = payments.filter(contract__landlord=user)

    else:
        payments = Payment.objects.none()

    payments = payments.order_by("-due_date")

    # =====================================================
    # STATS (ONLY ON FILTERED DATA)
    # =====================================================
    total_due = sum(
        p.amount for p in payments
        if p.status in ["pending", "overdue"]
    )

    total_paid = sum(
        p.amount for p in payments
        if p.status == "paid"
    )

    overdue = payments.filter(status="overdue").count()

    return render(request, "payments/payment_list.html", {
        "payments": payments,
        "total_due": total_due,
        "total_paid": total_paid,
        "overdue": overdue,
    })


# =====================================================
# MARK AS PAID (SECURE)
# =====================================================
@login_required
def mark_paid(request, pk):

    payment = get_object_or_404(Payment, pk=pk)
    user = request.user

    # =====================================================
    # STRICT PERMISSION CHECK
    # =====================================================
    allowed = (
        (user.role == "tenant" and payment.contract.tenant.user == user) or
        (user.role == "agent" and payment.contract.agent == user) or
        (user.role == "landlord" and payment.contract.landlord == user)
    )

    if not allowed:
        messages.error(request, "Not allowed.")
        return redirect("payment_list")

    if request.method == "POST":

        payment.status = "paid"
        payment.paid_date = timezone.now().date()
        payment.save(update_fields=["status", "paid_date"])

        messages.success(request, f"{payment.month} marked as paid.")

        # =====================================================
        # NOTIFY ONLY TENANT (REAL FLOW)
        # =====================================================
        create_notification(
            payment.contract.tenant.user,
            "Payment Received",
            f"Your rent for {payment.month} has been marked as paid.",
            type="payment"
        )

    return redirect("payment_list")


# =====================================================
# PAYMENT DETAIL (SECURE ACCESS)
# =====================================================
@login_required
def payment_detail(request, pk):

    payment = get_object_or_404(Payment, pk=pk)
    user = request.user

    allowed = (
        (user.role == "tenant" and payment.contract.tenant.user == user) or
        (user.role == "agent" and payment.contract.agent == user) or
        (user.role == "landlord" and payment.contract.landlord == user)
    )

    if not allowed:
        messages.error(request, "Access denied.")
        return redirect("dashboard")

    return render(request, "payments/payment_detail.html", {
        "payment": payment
    })


# =====================================================
# PROCESS PAYMENT (TENANT ONLY FIXED)
# =====================================================
@login_required
def process_payment(request, pk):

    payment = get_object_or_404(Payment, pk=pk)

    # ONLY TENANT CAN PAY
    if request.user.role != "tenant":
        messages.error(request, "Only tenants can pay.")
        return redirect("payment_list")

    # MUST OWN CONTRACT
    if payment.contract.tenant.user != request.user:
        messages.error(request, "Not allowed.")
        return redirect("payment_list")

    payment.status = "paid"
    payment.paid_date = timezone.now().date()
    payment.save()

    # =====================================================
    # NOTIFY LANDLORD (IMPORTANT FIX)
    # =====================================================
    create_notification(
        payment.contract.landlord,
        "Rent Paid",
        f"{payment.contract.tenant.user} paid rent for {payment.month}.",
        type="payment"
    )

    return redirect("payment_list")