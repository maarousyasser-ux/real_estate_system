from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import Notification


def create_notification(user, title, message, type=None):

    notif = Notification.objects.create(
        user=user,
        title=title,
        message=message,
        type=type or "general"
    )

    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        f"notif_{user.id}",
        {
            "type": "notify",
            "title": title,
            "message": message,
            "id": notif.id,
        }
    )

    return notif