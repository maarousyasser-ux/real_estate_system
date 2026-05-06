from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()


# =========================
# USER PROFILE
# =========================
class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('tenant', 'Tenant'),
        ('landlord', 'Landlord'),
        ('agent', 'Agent'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='tenant')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)
    verified = models.BooleanField(default=False)

    followers = models.ManyToManyField(
        'self', symmetrical=False, related_name='following', blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"

    def follower_count(self):
        return self.followers.count()

    def following_count(self):
        return self.following.count()


# =========================
# POST
# =========================
class Post(models.Model):
    POST_TYPES = [
        ('general', 'General'),
        ('question', 'Question'),
        ('tip', 'Tip & Advice'),
        ('listing', 'Property Listing'),
        ('announcement', 'Announcement'),
    ]

    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    content = models.TextField(max_length=2000)
    post_type = models.CharField(max_length=20, choices=POST_TYPES, default='general')
    image = models.ImageField(upload_to='posts/', blank=True, null=True)

    likes = models.ManyToManyField(UserProfile, related_name='liked_posts', blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_pinned = models.BooleanField(default=False)

    class Meta:
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return f"{self.author.username}: {self.content[:40]}"

    def like_count(self):
        return self.likes.count()

    def comment_count(self):
        return self.comments.count()


# =========================
# COMMENT (FIXED HERE)
# =========================
class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')

    # 🔥 FIX: make nullable TEMPORARILY
    author = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='comments',
        null=True,
        blank=True
    )

    content = models.TextField(max_length=1000)

    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies'
    )

    likes = models.ManyToManyField(UserProfile, related_name='liked_comments', blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        if self.author:
            return f"{self.author.user.username} on post {self.post.id}"
        return f"Anonymous comment on post {self.post.id}"


# =========================
# MESSAGE
# =========================
class Message(models.Model):
    sender = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='received_messages')

    content = models.TextField(max_length=2000)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.user.username} → {self.recipient.user.username}"


# =========================
# CONVERSATION (IMPROVED)
# =========================
class Conversation(models.Model):
    participants = models.ManyToManyField(UserProfile, related_name='conversations')

    # ❗ Better design: use FK instead of M2M for messages (optional improvement)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']


# =========================
# PROPERTY LISTING
# =========================
class PropertyListing(models.Model):
    LISTING_TYPES = [
        ('rent', 'For Rent'),
        ('sale', 'For Sale'),
        ('roommate', 'Roommate Wanted'),
    ]

    PROPERTY_TYPES = [
        ('apartment', 'Apartment'),
        ('house', 'House'),
        ('studio', 'Studio'),
        ('villa', 'Villa'),
        ('commercial', 'Commercial'),
    ]

    owner = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='listings')

    title = models.CharField(max_length=200)
    description = models.TextField(max_length=2000)

    listing_type = models.CharField(max_length=20, choices=LISTING_TYPES)
    property_type = models.CharField(max_length=20, choices=PROPERTY_TYPES)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    location = models.CharField(max_length=200)

    bedrooms = models.PositiveIntegerField(default=1)
    bathrooms = models.PositiveIntegerField(default=1)
    area_sqm = models.PositiveIntegerField(null=True, blank=True)

    image = models.ImageField(upload_to='listings/', blank=True, null=True)

    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    saved_by = models.ManyToManyField(UserProfile, related_name='saved_listings', blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def saved_count(self):
        return self.saved_by.count()


# =========================
# NOTIFICATION
# =========================
class Notification(models.Model):
    NOTIF_TYPES = [
        ('like', 'Liked your post'),
        ('comment', 'Commented on your post'),
        ('follow', 'Started following you'),
        ('message', 'Sent you a message'),
        ('listing', 'Interested in your listing'),
    ]

    recipient = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='sent_notifications')

    notif_type = models.CharField(max_length=20, choices=NOTIF_TYPES)

    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True)

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']