from django.urls import path
from django.contrib.auth import views as auth_views
from . import views




urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('register/', views.register_view, name='register'), 
    path('messages/', views.messages_view, name='messages'),
    path('community/', views.community_view, name='community'),
    path('profile/', views.profile_view, name='profile'),
    
    

    path('login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('password-change/', auth_views.PasswordChangeView.as_view(template_name='users/password_change.html'), name='password_change'),
   path('messages/', views.messages_view, name='messages'),
   path('delete-account/', views.delete_account_view, name='delete_account'),
   



  
]