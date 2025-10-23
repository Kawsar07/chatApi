# chat/consumers.py
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.conf import settings
from django.db import models
from datetime import datetime

logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        query_string = self.scope.get('query_string', b'').decode()
        params = dict(param.split('=') for param in query_string.split('&') if '=' in param)
        token = params.get('token')
        friend_username = params.get('friend_username')

        logger.debug(f"WebSocket connect attempt: path={self.scope['path']}, query={query_string}")

        if not token:
            await self._reject("Authentication failed: No token provided", 4003)
            return

        try:
            user = await self.get_user_from_token(token)
            if not user or not user.is_authenticated:
                logger.error(f"Invalid or unauthenticated user for token: {token}")
                await self._reject("Authentication failed: Invalid or expired token", 4001)
                return

            self.user = user
            self.room_group_name = 'chat_testroom'
            self.friend_username = friend_username
            logger.info(f"User authenticated: {user.username}, friend={friend_username}")

            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()
            logger.info(f"WebSocket connection accepted for user: {user.username}")

            profile = await self.get_profile(user)
            image_url = (
                f"{settings.WEBSOCKET_BASE_URL.rstrip('/')}{profile.picture.url}"
                if profile and profile.picture else ''
            )
            logger.debug(f"Connection image_url: {image_url}")

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_status',
                    'status': 'joined',
                    'user': user.username,
                    'image_url': image_url,
                }
            )

            await self.send(text_data=json.dumps({
                'type': 'status',
                'status': 'connected',
                'message': 'WebSocket connected successfully',
                'user': user.username,
                'image_url': image_url,
            }))

            if friend_username:
                messages = await self.get_previous_messages(user, friend_username)
                await self.send(text_data=json.dumps({
                    'type': 'previous_messages',
                    'messages': messages
                }))
            else:
                logger.debug("No friend_username provided; skipping previous messages")

        except Exception as e:
            logger.error(f"Connection error: {str(e)}", exc_info=True)
            await self._reject(f"Connection error: {str(e)}", 4000)

    async def disconnect(self, close_code):
        logger.debug(f"WebSocket disconnect: user={getattr(self, 'user', None)}, code={close_code}")
        if hasattr(self, 'user') and self.user.is_authenticated:
            try:
                profile = await self.get_profile(self.user)
                image_url = (
                    f"{settings.WEBSOCKET_BASE_URL.rstrip('/')}{profile.picture.url}"
                    if profile and profile.picture else ''
                )
                logger.debug(f"Disconnect image_url: {image_url}")
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'user_status',
                        'status': 'left',
                        'user': self.user.username,
                        'image_url': image_url,
                    }
                )
            except Exception as e:
                logger.error(f"Disconnect error: {str(e)}", exc_info=True)

        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        logger.debug(f"Received data: {text_data}")
        try:
            data = json.loads(text_data)
            message = data.get('message')
            receiver_username = data.get('receiver_username')

            if not message or not receiver_username:
                await self.send(text_data=json.dumps({
                    'error': 'Invalid message: message and receiver_username are required',
                    'code': 4004
                }))
                return

            if not hasattr(self, 'friend_username') or not self.friend_username:
                self.friend_username = receiver_username

            receiver = await self.get_user(receiver_username)
            if not receiver:
                await self.send(text_data=json.dumps({
                    'error': f'Receiver not found: {receiver_username}',
                    'code': 4005
                }))
                return

            try:
                message_obj = await self.create_message(self.user, receiver_username, message)
            except Exception as e:
                logger.error(f"Failed to save message: {str(e)}")
                await self.send(text_data=json.dumps({
                    'error': f'Failed to save message: {str(e)}',
                    'code': 4006
                }))
                return

            profile = await self.get_profile(self.user)
            image_url = (
                f"{settings.WEBSOCKET_BASE_URL.rstrip('/')}{profile.picture.url}"
                if profile and profile.picture else ''
            )
            logger.debug(f"Message image_url: {image_url}")

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'user': self.user.username,
                    'timestamp': message_obj.timestamp.isoformat() + 'Z',
                    'image_url': image_url,
                }
            )

            if not getattr(self, '_history_sent', False):
                self._history_sent = True
                messages = await self.get_previous_messages(self.user, receiver_username)
                await self.send(text_data=json.dumps({
                    'type': 'previous_messages',
                    'messages': messages
                }))

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'error': 'Invalid JSON format',
                'code': 4002
            }))
        except Exception as e:
            logger.error(f"Receive error: {str(e)}", exc_info=True)
            await self.send(text_data=json.dumps({
                'error': f'Internal server error: {str(e)}',
                'code': 4000
            }))

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'user': event['user'],
            'timestamp': event['timestamp'],
            'image_url': event['image_url'],
        }))

    async def user_status(self, event):
        await self.send(text_data=json.dumps({
            'type': 'status',
            'status': event['status'],
            'user': event['user'],
            'image_url': event['image_url'],
        }))

    async def _reject(self, message, code):
        await self.send(text_data=json.dumps({
            'error': message,
            'code': code
        }))
        await self.close(code=code)

    @database_sync_to_async
    def get_user_from_token(self, token_key):
        from rest_framework.authtoken.models import Token
        try:
            return Token.objects.select_related('user').get(key=token_key).user
        except Token.DoesNotExist:
            logger.warning(f"Token not found: {token_key}")
            return None

    @database_sync_to_async
    def get_profile(self, user):
        from .models import Profile
        try:
            return Profile.objects.get(user=user)
        except Profile.DoesNotExist:
            logger.warning(f"Profile not found for user {user.username}")
            return None

    @database_sync_to_async
    def get_user(self, username):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            logger.warning(f"User not found: {username}")
            return None

    @database_sync_to_async
    def create_message(self, sender, receiver_username, content):
        from .models import Message
        return Message.objects.create(
            sender=sender,
            receiver_username=receiver_username,
            content=content
        )

    @database_sync_to_async
    def get_previous_messages(self, user, friend_username, limit=50):
        from .models import Message
        from .serializers import MessageSerializer
        try:
            messages = Message.objects.filter(
                (models.Q(sender=user) & models.Q(receiver_username=friend_username)) |
                (models.Q(sender__username=friend_username) & models.Q(receiver_username=user.username))
            ).order_by('timestamp')[:limit]
            serializer = MessageSerializer(messages, many=True, context={'request': None})
            return serializer.data
        except Exception as e:
            logger.error(f"Database error fetching messages: {str(e)}")
            return []