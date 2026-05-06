import json
from channels.generic.websocket import AsyncWebsocketConsumer

class NotificationConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user = self.scope["user"]

        if self.user.is_anonymous:
            await self.close()
        else:
            self.group = f"notif_{self.user.id}"

            await self.channel_layer.group_add(
                self.group,
                self.channel_name
            )

            await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group,
            self.channel_name
        )

    async def send_notification(self, event):
        await self.send(text_data=json.dumps(event["data"]))
        
        
        
        
        
class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_group = f"chat_{self.room_id}"

        await self.channel_layer.group_add(
            self.room_group,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data["message"]
        user = self.scope["user"]

        await self.channel_layer.group_send(
            self.room_group,
            {
                "type": "chat_message",
                "message": message,
                "user": user.username
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))