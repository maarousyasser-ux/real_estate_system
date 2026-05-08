from django.db import models
from django.conf import settings


# =========================
# USER PROFILE (ONLY ONE VERSION)
# =========================
class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('tenant', 'Tenant'),
        ('landlord', 'Landlord'),
        ('agent', 'Agent'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile'
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='tenant')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(blank=True)
    location = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)

    followers = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='following',
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username


# =========================
# POST
# =========================
class Post(models.Model):
    POST_TYPES = [
        ('general', 'General'),
        ('question', 'Question'),
        ('tip', 'Tip'),
        ('listing', 'Listing'),
    ]

    author = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='posts'
    )

    content = models.TextField()
    post_type = models.CharField(max_length=20, choices=POST_TYPES, default='general')
    image = models.ImageField(upload_to='posts/', blank=True, null=True)

    likes = models.ManyToManyField(UserProfile, related_name='liked_posts', blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def like_count(self):
        return self.likes.count()


# =========================
# COMMENT
# =========================
class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')

    author = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='comments',
        null=True,
        blank=True
    )

    content = models.TextField()

    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies'
    )

    created_at = models.DateTimeField(auto_now_add=True)


# =========================
# MESSAGE
# =========================
class Message(models.Model):
    sender = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='received_messages')

    content = models.TextField()
    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)


# =========================
# CONVERSATION
# =========================
class Conversation(models.Model):
    participants = models.ManyToManyField(UserProfile, related_name='conversations')

    updated_at = models.DateTimeField(auto_now=True)


# =========================
# LISTING (FIXED FIELDS)
# =========================
class PropertyListing(models.Model):
    LISTING_TYPES = [
        ('rent', 'Rent'),
        ('sale', 'Sale'),
    ]

    PROPERTY_TYPES = [
        ('apartment', 'Apartment'),
        ('house', 'House'),
        ('studio', 'Studio'),
    ]

    owner = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='listings')

    title = models.CharField(max_length=200)
    description = models.TextField()

    listing_type = models.CharField(max_length=20, choices=LISTING_TYPES)
    property_type = models.CharField(max_length=20, choices=PROPERTY_TYPES)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    location = models.CharField(max_length=200)

    bedrooms = models.IntegerField(default=1)
    bathrooms = models.IntegerField(default=1)
    area_sqm = models.IntegerField(null=True, blank=True)

    image = models.ImageField(upload_to='listings/', blank=True, null=True)

    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


# =========================
# NOTIFICATION
# =========================
class Notification(models.Model):
    recipient = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='sent_notifications')

    notif_type = models.CharField(max_length=20)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True)

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)