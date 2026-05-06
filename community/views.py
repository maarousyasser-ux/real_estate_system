from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
User = get_user_model()
from django.http import JsonResponse
from django.db.models import Q, Count
from django.contrib import messages
from django.utils import timezone
from django.core.paginator import Paginator
from .models import (
    UserProfile, Post, Comment, Message,
    Conversation, PropertyListing, Notification
)
from .forms import PostForm, CommentForm, ProfileForm, ListingForm, MessageForm


# ─── FEED / HOME ──────────────────────────────────────────────────────────────

@login_required
def community_feed(request):
    profile = get_object_or_404(UserProfile, user=request.user)

    # Posts from followed users + own posts
    following_ids = profile.following.values_list('id', flat=True)
    posts = Post.objects.filter(
        Q(author__in=following_ids) | Q(author=profile)
    ).select_related('author__user').prefetch_related('likes', 'comments').order_by('-is_pinned', '-created_at')

    # Filter by type
    post_type = request.GET.get('type', '')
    if post_type:
        posts = posts.filter(post_type=post_type)

    paginator = Paginator(posts, 10)
    page = request.GET.get('page', 1)
    posts_page = paginator.get_page(page)

    # Suggested users to follow (not already following, not self)
    suggested_users = UserProfile.objects.exclude(
        id__in=following_ids
    ).exclude(id=profile.id).annotate(
        follower_count=Count('followers')
    ).order_by('-follower_count')[:5]

    # Recent listings
    recent_listings = PropertyListing.objects.filter(
        is_available=True
    ).select_related('owner__user')[:4]

    post_form = PostForm()
    unread_notifications = profile.notifications.filter(is_read=False).count()
    unread_messages = Message.objects.filter(recipient=profile, is_read=False).count()

    context = {
        'profile': profile,
        'posts': posts_page,
        'suggested_users': suggested_users,
        'recent_listings': recent_listings,
        'post_form': post_form,
        'post_types': Post.POST_TYPES,
        'active_type': post_type,
        'unread_notifications': unread_notifications,
        'unread_messages': unread_messages,
    }
    return render(request, 'community/feed.html', context)


# ─── POSTS ────────────────────────────────────────────────────────────────────

@login_required
def create_post(request):
    if request.method == 'POST':
        profile = get_object_or_404(UserProfile, user=request.user)
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = profile
            post.save()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'post_id': post.id})
            messages.success(request, 'Post created successfully!')
        else:
            messages.error(request, 'Error creating post.')
    return redirect('community:feed')


@login_required
def post_detail(request, pk):
    post = get_object_or_404(Post, pk=pk)
    profile = get_object_or_404(UserProfile, user=request.user)
    comments = post.comments.filter(parent=None).select_related(
        'author__user'
    ).prefetch_related('replies__author__user')
    comment_form = CommentForm()

    context = {
        'profile': profile,
        'post': post,
        'comments': comments,
        'comment_form': comment_form,
        'user_liked': post.likes.filter(id=profile.id).exists(),
    }
    return render(request, 'community/post_detail.html', context)


@login_required
def delete_post(request, pk):
    post = get_object_or_404(Post, pk=pk)
    profile = get_object_or_404(UserProfile, user=request.user)
    if post.author == profile:
        post.delete()
        messages.success(request, 'Post deleted.')
    return redirect('community:feed')


@login_required
def toggle_like(request, pk):
    post = get_object_or_404(Post, pk=pk)
    profile = get_object_or_404(UserProfile, user=request.user)
    if profile in post.likes.all():
        post.likes.remove(profile)
        liked = False
    else:
        post.likes.add(profile)
        liked = True
        if post.author != profile:
            Notification.objects.create(
                recipient=post.author, sender=profile,
                notif_type='like', post=post
            )
    return JsonResponse({'liked': liked, 'count': post.like_count()})


@login_required
def add_comment(request, pk):
    post = get_object_or_404(Post, pk=pk)
    profile = get_object_or_404(UserProfile, user=request.user)
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = profile
            parent_id = request.POST.get('parent_id')
            if parent_id:
                comment.parent = get_object_or_404(Comment, pk=parent_id)
            comment.save()
            if post.author != profile:
                Notification.objects.create(
                    recipient=post.author, sender=profile,
                    notif_type='comment', post=post
                )
    return redirect('community:post_detail', pk=pk)


# ─── PROFILES ─────────────────────────────────────────────────────────────────

@login_required
def user_profile(request, username):
    user = get_object_or_404(User, username=username)
    viewed_profile = get_object_or_404(UserProfile, user=user)
    my_profile = get_object_or_404(UserProfile, user=request.user)

    posts = Post.objects.filter(author=viewed_profile).select_related('author__user')
    listings = PropertyListing.objects.filter(owner=viewed_profile, is_available=True)
    is_following = my_profile in viewed_profile.followers.all()

    context = {
        'profile': my_profile,
        'viewed_profile': viewed_profile,
        'posts': posts,
        'listings': listings,
        'is_following': is_following,
        'is_own_profile': my_profile == viewed_profile,
        'post_count': posts.count(),
        'follower_count': viewed_profile.follower_count(),
        'following_count': viewed_profile.following_count(),
    }
    return render(request, 'community/profile.html', context)


@login_required
def edit_profile(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            # Update user first/last name
            request.user.first_name = request.POST.get('first_name', '')
            request.user.last_name = request.POST.get('last_name', '')
            request.user.save()
            messages.success(request, 'Profile updated!')
            return redirect('community:profile', username=request.user.username)
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'community/edit_profile.html', {'profile': profile, 'form': form})


@login_required
def toggle_follow(request, username):
    target_user = get_object_or_404(User, username=username)
    target_profile = get_object_or_404(UserProfile, user=target_user)
    my_profile = get_object_or_404(UserProfile, user=request.user)

    if my_profile == target_profile:
        return JsonResponse({'error': 'Cannot follow yourself'}, status=400)

    if my_profile in target_profile.followers.all():
        target_profile.followers.remove(my_profile)
        following = False
    else:
        target_profile.followers.add(my_profile)
        following = True
        Notification.objects.create(
            recipient=target_profile, sender=my_profile, notif_type='follow'
        )
    return JsonResponse({'following': following, 'count': target_profile.follower_count()})


@login_required
def members_list(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    role_filter = request.GET.get('role', '')
    search = request.GET.get('q', '')

    members = UserProfile.objects.select_related('user').annotate(
        follower_count=Count('followers')
    ).order_by('-follower_count')

    if role_filter:
        members = members.filter(role=role_filter)
    if search:
        members = members.filter(
            Q(user__username__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(location__icontains=search)
        )

    paginator = Paginator(members, 12)
    page = request.GET.get('page', 1)
    members_page = paginator.get_page(page)

    context = {
        'profile': profile,
        'members': members_page,
        'role_filter': role_filter,
        'search': search,
    }
    return render(request, 'community/members.html', context)


# ─── MESSAGES ─────────────────────────────────────────────────────────────────

@login_required
def inbox(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    conversations = profile.conversations.prefetch_related(
        'participants__user', 'messages'
    ).order_by('-updated_at')

    context = {
        'profile': profile,
        'conversations': conversations,
        'unread_total': Message.objects.filter(recipient=profile, is_read=False).count(),
    }
    return render(request, 'community/inbox.html', context)


@login_required
def conversation(request, username):
    other_user = get_object_or_404(User, username=username)
    other_profile = get_object_or_404(UserProfile, user=other_user)
    my_profile = get_object_or_404(UserProfile, user=request.user)

    # Get or create conversation
    conv = Conversation.objects.filter(
        participants=my_profile
    ).filter(participants=other_profile).first()

    if not conv:
        conv = Conversation.objects.create()
        conv.participants.add(my_profile, other_profile)

    # Mark messages as read
    conv.messages.filter(recipient=my_profile, is_read=False).update(is_read=True)

    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.sender = my_profile
            msg.recipient = other_profile
            msg.save()
            conv.messages.add(msg)
            conv.save()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'content': msg.content,
                    'time': msg.created_at.strftime('%H:%M'),
                })
            return redirect('community:conversation', username=username)

    msgs = conv.messages.all().order_by('created_at')
    form = MessageForm()

    context = {
        'profile': my_profile,
        'other_profile': other_profile,
        'conversation': conv,
        'messages_list': msgs,
        'form': form,
    }
    return render(request, 'community/conversation.html', context)


# ─── LISTINGS ─────────────────────────────────────────────────────────────────

@login_required
def listings(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    listing_type = request.GET.get('type', '')
    property_type = request.GET.get('property', '')
    search = request.GET.get('q', '')

    all_listings = PropertyListing.objects.filter(
        is_available=True
    ).select_related('owner__user').order_by('-created_at')

    if listing_type:
        all_listings = all_listings.filter(listing_type=listing_type)
    if property_type:
        all_listings = all_listings.filter(property_type=property_type)
    if search:
        all_listings = all_listings.filter(
            Q(title__icontains=search) | Q(location__icontains=search)
        )

    paginator = Paginator(all_listings, 9)
    page = request.GET.get('page', 1)
    listings_page = paginator.get_page(page)

    context = {
        'profile': profile,
        'listings': listings_page,
        'listing_types': PropertyListing.LISTING_TYPES,
        'property_types': PropertyListing.PROPERTY_TYPES,
        'active_type': listing_type,
        'active_property': property_type,
        'search': search,
    }
    return render(request, 'community/listings.html', context)


@login_required
def create_listing(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    if profile.role not in ['landlord', 'agent']:
        messages.error(request, 'Only landlords and agents can create listings.')
        return redirect('community:listings')

    if request.method == 'POST':
        form = ListingForm(request.POST, request.FILES)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.owner = profile
            listing.save()
            messages.success(request, 'Listing created!')
            return redirect('community:listings')
    else:
        form = ListingForm()

    return render(request, 'community/create_listing.html', {'profile': profile, 'form': form})


@login_required
def toggle_save_listing(request, pk):
    listing = get_object_or_404(PropertyListing, pk=pk)
    profile = get_object_or_404(UserProfile, user=request.user)
    if profile in listing.saved_by.all():
        listing.saved_by.remove(profile)
        saved = False
    else:
        listing.saved_by.add(profile)
        saved = True
    return JsonResponse({'saved': saved, 'count': listing.saved_count()})


# ─── NOTIFICATIONS ─────────────────────────────────────────────────────────────

@login_required
def notifications(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    notifs = profile.notifications.select_related(
        'sender__user', 'post'
    ).order_by('-created_at')
    notifs.filter(is_read=False).update(is_read=True)

    context = {
        'profile': profile,
        'notifications': notifs,
    }
    return render(request, 'community/notifications.html', context)


@login_required
def mark_notifications_read(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    profile.notifications.filter(is_read=False).update(is_read=True)
    return JsonResponse({'success': True})