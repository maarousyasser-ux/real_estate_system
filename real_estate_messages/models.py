from django.db import models
from django.conf import settings
from django.contrib.auth.models import User


class Conversation(models.Model):
    """A conversation thread between two users."""
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='conversations'
    )
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)  # bumped on each new message

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        names = ', '.join(u.username for u in self.participants.all())
        return f"Conversation({names})"

    def last_message(self):
        return self.messages.order_by('-created_at').first()

    def unread_count(self, user):
        return self.messages.filter(is_read=False).exclude(sender=user).count()

    @staticmethod
    def get_or_create_between(user_a, user_b):
        """Return existing conversation between two users, or create one."""
        shared = Conversation.objects.filter(
            participants=user_a
        ).filter(
            participants=user_b
        )
        if shared.exists():
            return shared.first(), False
        conv = Conversation.objects.create()
        conv.participants.add(user_a, user_b)
        return conv, True


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender    = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    content   = models.TextField()
    is_read   = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.username}: {self.content[:40]}"