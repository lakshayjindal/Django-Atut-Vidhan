import json
from channels.generic.websocket import AsyncWebsocketConsumer

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # user_id comes from the URL pattern ws/chat/<user_id>/
        self.chat_with = self.scope["url_route"]["kwargs"]["user_id"]
        self.room_group_name = f"chat_{self.chat_with}"

        # join group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # leave group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get("message")

        # broadcast to everyone in the group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message
            }
        )

    async def chat_message(self, event):
        # send message to WebSocket
        await self.send(text_data=json.dumps({
            "message": event["message"]
        }))
