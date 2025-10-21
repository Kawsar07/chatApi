import json
import redis
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Message, Profile
from django.contrib.auth.models import User
from knox.auth import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed

redis_client = redis.Redis(host='127.0.0.1', port=6379, db=0)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'
        
        try:
            token = self.scope['query_string'].decode().split('token=')[1]
            token_auth = TokenAuthentication()
            user, _ = await database_sync_to_async(token_auth.authenticate_credentials)(token.encode())
            self.scope['user'] = user
        except (IndexError, AuthenticationFailed):
            await self.close()
            return

        await database_sync_to_async(redis_client.set)(f'user:{user.username}:active', 1, ex=60)
        
        try:
            profile = await database_sync_to_async(Profile.objects.get)(user=user)
            picture_url = profile.picture.url if profile.picture else ''
            location = profile.location
        except Profile.DoesNotExist:
            picture_url = ''
            location = ''
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status',
                'username': user.username,
                'status': 'joined',
                'picture': picture_url,
                'location': location,
            }
        )

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'scope') and 'user' in self.scope and self.scope['user'].is_authenticated:
            user = self.scope['user']
            await database_sync_to_async(redis_client.delete)(f'user:{user.username}:active')
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_status',
                    'username': user.username,
                    'status': 'left',
                    'picture': '',
                    'location': '',
                }
            )
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        user = self.scope['user'] if self.scope['user'].is_authenticated else None

        if not user:
            user = await database_sync_to_async(User.objects.get)(username='testuser')

        try:
            profile = await database_sync_to_async(Profile.objects.get)(user=user)
            picture_url = profile.picture.url if profile.picture else ''
        except Profile.DoesNotExist:
            picture_url = ''

        await self.save_message(user, message, self.room_name)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'user': user.username,
                'picture': picture_url,
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'user': event['user'],
            'picture': event['picture'],
        }))

    async def user_status(self, event):
        await self.send(text_data=json.dumps({
            'type': 'status',
            'username': event['username'],
            'status': event['status'],
            'picture': event['picture'],
            'location': event['location'],
        }))

    @database_sync_to_async
    def save_message(self, user, content, room):
        Message.objects.create(user=user, content=content, room=room)