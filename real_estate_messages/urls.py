from django.urls import path
from . import views

app_name = 'real_estate_messages'

urlpatterns = [
    path('', views.inbox, name='inbox'),

    path('start/<int:user_id>/', views.start_conversation, name='start_conversation'),

    path('conversation/<int:conv_id>/', views.conversation, name='conversation'),

    path('send/<int:conv_id>/', views.send_message_ajax, name='send_message_ajax'),

    path('poll/<int:conv_id>/', views.poll_messages, name='poll_messages'),
]