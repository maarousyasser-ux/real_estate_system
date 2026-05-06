from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

from .models import Notification

@login_required
def notifications_list(request):
    print("CURRENT USER:", request.user.username)

    notifications = request.user.notifications.all()

    return render(request, "notifications/notifications_list.html", {
        "notifications": notifications
    })
@login_required
def mark_as_read(request, pk):
    notif = get_object_or_404(
        Notification,
        pk=pk,
        user=request.user
    )

    notif.is_read = True
    notif.save(update_fields=["is_read"])

    return redirect("notifications_list")