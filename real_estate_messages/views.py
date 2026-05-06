from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import Conversation, Message


from notifications.models import Notification

def get_user_notifications(user):
    return Notification.objects.filter(user=user).order_by("-created_at")

User = get_user_model()


@login_required
def inbox(request):
    conversations = request.user.conversations.prefetch_related(
        'participants', 'messages'
    ).order_by('-updated_at')

    conv_data = []
    for conv in conversations:
        other = conv.participants.exclude(id=request.user.id).first()
        conv_data.append({
            'conv':         conv,
            'other':        other,
            'last_message': conv.last_message(),
            'unread':       conv.unread_count(request.user),
        })

    all_users = User.objects.exclude(id=request.user.id).order_by('username')

    return render(request, 'users/messages.html', {
        'conv_data':   conv_data,
        'all_users':   all_users,
        'active_conv': None,
    })


@login_required
def conversation(request, conv_id):
    conv = get_object_or_404(Conversation, id=conv_id, participants=request.user)

    conv.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)

    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            Message.objects.create(
                conversation=conv,
                sender=request.user,
                content=content,
            )
            conv.save()
        # ✅ FIXED: use correct namespace
        return redirect('real_estate_messages:conversation', conv_id=conv.id)

    conversations = request.user.conversations.prefetch_related(
        'participants', 'messages'
    ).order_by('-updated_at')

    conv_data = []
    for c in conversations:
        other = c.participants.exclude(id=request.user.id).first()
        conv_data.append({
            'conv':         c,
            'other':        other,
            'last_message': c.last_message(),
            'unread':       c.unread_count(request.user),
        })

    other_user = conv.participants.exclude(id=request.user.id).first()
    all_users  = User.objects.exclude(id=request.user.id).order_by('username')

    return render(request, 'users/messages.html', {
        'conv_data':     conv_data,
        'all_users':     all_users,
        'active_conv':   conv,
        'other_user':    other_user,
        'messages_list': conv.messages.select_related('sender').all(),
    })


@login_required
def start_conversation(request, user_id):
    other = get_object_or_404(User, id=user_id)

    if other == request.user:
        return redirect('real_estate_messages:inbox')  # ✅ FIXED

    conv, _ = Conversation.get_or_create_between(request.user, other)
    return redirect('real_estate_messages:conversation', conv_id=conv.id)  # ✅ FIXED


@login_required
@require_POST
def send_message_ajax(request, conv_id):
    conv    = get_object_or_404(Conversation, id=conv_id, participants=request.user)
    content = request.POST.get('content', '').strip()

    if not content:
        return JsonResponse({'error': 'Empty message'}, status=400)

    msg = Message.objects.create(
        conversation=conv,
        sender=request.user,
        content=content,
    )
    conv.save()

    return JsonResponse({
        'id':         msg.id,
        'content':    msg.content,
        'sender_id':  msg.sender.id,
        'created_at': msg.created_at.strftime('%H:%M'),
        'is_mine':    True,
    })


@login_required
def poll_messages(request, conv_id):
    conv     = get_object_or_404(Conversation, id=conv_id, participants=request.user)
    since_id = int(request.GET.get('since', 0))

    new_msgs = conv.messages.filter(id__gt=since_id).select_related('sender')
    new_msgs.filter(is_read=False).exclude(sender=request.user).update(is_read=True)

    data = [{
        'id':       m.id,
        'content':  m.content,
        'sender':   m.sender.get_full_name() or m.sender.username,
        'initials': (m.sender.username[0] + (m.sender.last_name[0] if m.sender.last_name else '')).upper(),
        'is_mine':  m.sender == request.user,
        'time':     m.created_at.strftime('%H:%M'),
    } for m in new_msgs]

    return JsonResponse({'messages': data})