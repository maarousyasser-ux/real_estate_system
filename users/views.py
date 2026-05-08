from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from .forms import CustomUserCreationForm


from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum

from .forms import CustomUserCreationForm


from maintenance.models import MaintenanceRequest

from notifications.models import Notification

def get_user_notifications(user):
    return Notification.objects.filter(user=user).order_by("-created_at")

User = get_user_model()





@login_required
def dashboard_view(request):

    user = request.user
    context = {}

    # -------------------------
    # LANDLORD DASHBOARD
    # -------------------------
    if user.role == "landlord":

        from contracts.models import Contract
        from payments.models import Payment
        from properties.models import Property

        contracts = Contract.objects.filter(landlord=user, status="active")
        properties = Property.objects.filter(owner=user)

        total_revenue = Payment.objects.filter(
            contract__landlord=user,
            status="paid"
        ).aggregate(total=Sum("amount"))["total"] or 0

        context.update({
            "total_revenue": total_revenue,
            "active_tenants": contracts.count(),
            "available_units": properties.filter(status="available").count(),
        })

    # -------------------------
    # TENANT DASHBOARD
    # -------------------------
    elif user.role == "tenant":

        from contracts.models import Contract
        from payments.models import Payment
        from properties.models import Property

        current_lease = Contract.objects.select_related("property").filter(
            tenant__user=user,
            status="active"
        ).first()

        payments = []
        payments_made_count = 0
        rent_due = False
        rent_days_left = None
        rent_amount = 0
        next_due_date = None

        if current_lease:

            all_payments = Payment.objects.filter(
                contract=current_lease
            ).order_by("-due_date")   # FIXED TYPO

            payments = all_payments[:5]

            payments_made_count = all_payments.filter(
                status="paid"
            ).count()

            next_payment = all_payments.filter(
                status__in=["pending", "overdue"]
            ).order_by("due_date").first()

            if next_payment:
                rent_due = True
                rent_amount = next_payment.amount
                next_due_date = next_payment.due_date

                rent_days_left = (next_payment.due_date - timezone.now().date()).days

        available_properties = Property.objects.filter(status="available")[:3]

        context.update({
            "current_lease": current_lease,
            "payments": payments,
            "payments_made_count": payments_made_count,
            "rent_due": rent_due,
            "rent_amount": rent_amount,
            "next_due_date": next_due_date,
            "rent_days_left": max(0, rent_days_left) if rent_days_left else 0,
            "available_properties": available_properties,
            "open_requests_count": 0,
        })

    return render(request, "users/dashboard.html", context)

# PUBLIC VIEW: No @login_required here!
def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()

    return render(request, 'users/register.html', {'form': form})


@login_required
def profile_view(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.save()
        return redirect('profile')
    return render(request, 'users/profile.html')







@login_required
def messages_view(request):
    # This matches the 'messages' path in your URLs
    return render(request, 'users/messages.html')

@login_required
def community_view(request):
    # This matches the 'community' path in your URLs
    return render(request, 'community/feed.html')



@login_required
def maintenance_dashboard(request):

    user = request.user

    if user.role == "tenant":
        requests = MaintenanceRequest.objects.filter(
            tenant__user=user
        )

    elif user.role == "landlord":
        requests = MaintenanceRequest.objects.filter(
            property__owner=user
        )

    else:  # agent
        requests = MaintenanceRequest.objects.filter(
            property__agent=user
        )

    print("DEBUG COUNT:", requests.count())  # 🔍 important

    return render(request, "maintenance/dashboard.html", {
        "requests": requests
    })
    
    
    
    
    
    
