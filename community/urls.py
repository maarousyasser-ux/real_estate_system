from django.urls import path
from . import views

app_name = 'community'

urlpatterns = [
    # Feed
    path('', views.community_feed, name='feed'),

    # Posts
    path('post/create/', views.create_post, name='create_post'),
    path('post/<int:pk>/', views.post_detail, name='post_detail'),
    path('post/<int:pk>/delete/', views.delete_post, name='delete_post'),
    path('post/<int:pk>/like/', views.toggle_like, name='toggle_like'),
    path('post/<int:pk>/comment/', views.add_comment, name='add_comment'),

    # Profiles
    path('members/', views.members_list, name='members'),
    path('profile/<str:username>/', views.user_profile, name='profile'),
    path('profile/edit/me/', views.edit_profile, name='edit_profile'),
    path('profile/<str:username>/follow/', views.toggle_follow, name='toggle_follow'),

    # Messages
    path('messages/', views.inbox, name='inbox'),
    path('messages/<str:username>/', views.conversation, name='conversation'),

    # Listings
    path('listings/', views.listings, name='listings'),
    path('listings/create/', views.create_listing, name='create_listing'),
    path('listings/<int:pk>/save/', views.toggle_save_listing, name='toggle_save_listing'),

    # Notifications
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/read/', views.mark_notifications_read, name='mark_notifications_read'),
]