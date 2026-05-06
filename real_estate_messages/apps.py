# messages/apps.py
from django.apps import AppConfig


class MessagesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'real_estate_messages'  # Must match the folder name
    label = 're_messages'          # THIS MUST BE UNIQUE (not "messages")