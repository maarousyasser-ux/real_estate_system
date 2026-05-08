# community/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from .models import UserProfile, Post, Comment, Message, Conversation, PropertyListing, Notification
from .forms import PostForm, CommentForm, ProfileForm, ListingForm, MessageForm

User = get_user_model()


def get_profile(user):
    """Helper — always returns a UserProfile, creates one if missing."""
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={'role': getattr(user, 'role', 'tenant')}
    )
    return profile


# ── FEED ──────────────────────────────────────────────────────────────────────
@login_required
def community_feed(request):
    profile = get_profile(request.user)
    filter_by = request.GET.get('filter', 'all')

    posts = Post.objects.select_related('author__user').prefetch_related('likes', 'comments')

    if filter_by == 'following':
        followed = profile.following.all()
        posts = posts.filter(author__in=followed)
    elif filter_by in ['landlord', 'agent', 'tenant']:
        posts = posts.filter(author__role=filter_by)

    posts = posts.order_by('-created_at')

    suggested = UserProfile.objects.exclude(user=request.user).exclude(
        pk__in=profile.following.all()
    )[:5]

    return render(request, 'community/feed.html', {
        'posts': posts,
        'suggested_users': suggested,
        'profile': profile,
    })


# ── CREATE POST ───────────────────────────────────────────────────────────────
@login_required
def create_post(request):
    if request.method == 'POST':
        profile = get_profile(request.user)
        # Inject default post_type so the field is never empty
        data = request.POST.copy()
        if not data.get('post_type'):
            data['post_type'] = 'general'

        form = PostForm(data, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = profile
            post.save()
            messages.success(request, "Post shared!")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")

    return redirect('community:feed')


# ── POST DETAIL ───────────────────────────────────────────────────────────────
@login_required
def post_detail(request, pk):
    post = get_object_or_404(Post.objects.select_related('author__user'), pk=pk)
    comments = post.comments.select_related('author__user').filter(parent=None).order_by('created_at')
    return render(request, 'community/post_detail.html', {
        'post': post,
        'comments': comments,
        'profile': get_profile(request.user),
    })


# ── DELETE POST ───────────────────────────────────────────────────────────────
@login_required
def delete_post(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if post.author == get_profile(request.user):
        post.delete()
        messages.success(request, "Post deleted.")
    return redirect('community:feed')


# ── TOGGLE LIKE ───────────────────────────────────────────────────────────────
@login_required
def toggle_like(request, pk):
    post = get_object_or_404(Post, pk=pk)
    profile = get_profile(request.user)
    if profile in post.likes.all():
        post.likes.remove(profile)
    else:
        post.likes.add(profile)
        if post.author != profile:
            Notification.objects.create(
                recipient=post.author,
                sender=profile,
                notif_type='like',
                post=post,
            )
    return redirect(request.META.get('HTTP_REFERER', 'community:feed'))


# ── ADD COMMENT ───────────────────────────────────────────────────────────────
@login_required
def add_comment(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.method == 'POST':
        profile = get_profile(request.user)
        content = request.POST.get('content', '').strip()
        if content:
            Comment.objects.create(post=post, author=profile, content=content)
            if post.author != profile:
                Notification.objects.create(
                    recipient=post.author,
                    sender=profile,
                    notif_type='comment',
                    post=post,
                )
    return redirect(request.META.get('HTTP_REFERER', 'community:feed'))


# ── MEMBERS ───────────────────────────────────────────────────────────────────
@login_required
def members_list(request):
    q    = request.GET.get('q', '')
    role = request.GET.get('role', '')
    members = UserProfile.objects.select_related('user').exclude(user=request.user)
    if q:
        members = members.filter(user__username__icontains=q) | members.filter(user__first_name__icontains=q)
    if role:
        members = members.filter(role=role)
    return render(request, 'community/members.html', {
        'members': members,
        'profile': get_profile(request.user),
    })


# ── USER PROFILE ──────────────────────────────────────────────────────────────
@login_required
def user_profile(request, username):
    target_user = get_object_or_404(User, username=username)
    target_profile = get_profile(target_user)
    my_profile = get_profile(request.user)
    posts = Post.objects.filter(author=target_profile).order_by('-created_at')
    is_following = my_profile in target_profile.followers.all()
    return render(request, 'community/profile.html', {
        'profile_user': target_user,
        'target_profile': target_profile,
        'posts': posts,
        'is_following': is_following,
        'profile': my_profile,
    })


# ── EDIT PROFILE ─────────────────────────────────────────────────────────────
@login_required
def edit_profile(request):
    profile = get_profile(request.user)
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            # Save first/last name back to User
            request.user.first_name = request.POST.get('first_name', '')
            request.user.last_name  = request.POST.get('last_name', '')
            request.user.save()
            form.save()
            messages.success(request, "Profile updated.")
            return redirect('community:profile', username=request.user.username)
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'community/edit_profile.html', {
        'form': form,
        'profile': profile,
    })


# ── TOGGLE FOLLOW ─────────────────────────────────────────────────────────────
@login_required
def toggle_follow(request, username):
    target_user = get_object_or_404(User, username=username)
    target_profile = get_profile(target_user)
    my_profile = get_profile(request.user)
    if my_profile in target_profile.followers.all():
        target_profile.followers.remove(my_profile)
    else:
        target_profile.followers.add(my_profile)
        Notification.objects.create(
            recipient=target_profile,
            sender=my_profile,
            notif_type='follow',
        )
    return redirect(request.META.get('HTTP_REFERER', 'community:feed'))


# ── INBOX ─────────────────────────────────────────────────────────────────────
@login_required
def inbox(request):
    profile = get_profile(request.user)
    conversations = Conversation.objects.filter(participants=profile).prefetch_related('participants')
    conv_data = []
    for conv in conversations:
        other = conv.participants.exclude(pk=profile.pk).first()
        last_msg = Message.objects.filter(
            sender__in=[profile, other],
            recipient__in=[profile, other]
        ).order_by('-created_at').first()
        conv_data.append({
            'other_user': other.user if other else None,
            'last_message': last_msg.content if last_msg else '',
            'last_time': last_msg.created_at if last_msg else conv.updated_at,
            'unread': Message.objects.filter(recipient=profile, sender=other, is_read=False).exists(),
        })
    return render(request, 'community/inbox.html', {
        'conversations': conv_data,
        'profile': profile,
    })


# ── CONVERSATION ──────────────────────────────────────────────────────────────
@login_required
def conversation(request, username):
    other_user = get_object_or_404(User, username=username)
    my_profile    = get_profile(request.user)
    other_profile = get_profile(other_user)

    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            Message.objects.create(
                sender=my_profile,
                recipient=other_profile,
                content=content,
            )
            # ensure conversation exists
            conv, _ = Conversation.objects.get_or_create_for(my_profile, other_profile)
        return redirect('community:conversation', username=username)

    # Mark messages as read
    Message.objects.filter(sender=other_profile, recipient=my_profile, is_read=False).update(is_read=True)

    msgs = Message.objects.filter(
        sender__in=[my_profile, other_profile],
        recipient__in=[my_profile, other_profile],
    ).order_by('created_at')

    # sidebar conversations
    conversations = Conversation.objects.filter(participants=my_profile)
    conv_data = []
    for conv in conversations:
        other = conv.participants.exclude(pk=my_profile.pk).first()
        last_msg = Message.objects.filter(
            sender__in=[my_profile, other],
            recipient__in=[my_profile, other]
        ).order_by('-created_at').first()
        conv_data.append({
            'other_user': other.user if other else None,
            'last_message': last_msg.content if last_msg else '',
        })

    return render(request, 'community/conversation.html', {
        'other_user': other_user,
        'messages': msgs,
        'conversations': conv_data,
        'profile': my_profile,
    })


# ── LISTINGS ──────────────────────────────────────────────────────────────────
@login_required
def listings(request):
    q    = request.GET.get('q', '')
    type_ = request.GET.get('type', '')
    qs = PropertyListing.objects.select_related('owner__user').filter(is_available=True)
    if q:
        qs = qs.filter(title__icontains=q) | qs.filter(location__icontains=q)
    if type_:
        qs = qs.filter(property_type=type_)
    sort = request.GET.get('sort', 'newest')
    if sort == 'price_asc':
        qs = qs.order_by('price')
    elif sort == 'price_desc':
        qs = qs.order_by('-price')
    else:
        qs = qs.order_by('-created_at')
    return render(request, 'community/listings.html', {
        'listings': qs,
        'profile': get_profile(request.user),
    })


@login_required
def create_listing(request):
    if request.method == 'POST':
        profile = get_profile(request.user)
        form = ListingForm(request.POST, request.FILES)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.owner = profile
            listing.save()
            messages.success(request, "Listing posted!")
        else:
            messages.error(request, "Please fix the errors below.")
    return redirect('community:listings')


@login_required
def toggle_save_listing(request, pk):
    # PropertyListing has no saved_by field yet — skip silently
    return redirect('community:listings')


# ── NOTIFICATIONS ─────────────────────────────────────────────────────────────
@login_required
def notifications(request):
    profile = get_profile(request.user)
    notifs = Notification.objects.filter(recipient=profile).select_related(
        'sender__user', 'post'
    ).order_by('-created_at')
    return render(request, 'community/notifications.html', {
        'notifications': notifs,
        'profile': profile,
    })


@login_required
def mark_notifications_read(request):
    if request.method == 'POST':
        profile = get_profile(request.user)
        Notification.objects.filter(recipient=profile, is_read=False).update(is_read=True)
    return redirect('community:notifications')