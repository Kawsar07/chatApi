from django.contrib.auth import authenticate, login
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from django.db import models
from .models import Profile, Friend, FriendRequest, Message
from .serializers import UserSerializer, MessageSerializer, GetProfileSerializer, PutProfileSerializer, FriendSerializer
import logging

logger = logging.getLogger(__name__)

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        logger.debug(f"Login attempt for username: {username}")
        if not username or not password:
            logger.warning("Missing username or password")
            return Response({'error': 'Username and password are required'}, status=status.HTTP_400_BAD_REQUEST)
        user = authenticate(username=username, password=password)
        if user:
            login(request, user)
            token, created = Token.objects.get_or_create(user=user)
            logger.info(f"Login successful for {username}, token: {token.key}")
            return Response({'token': token.key, 'username': user.username}, status=status.HTTP_200_OK)
        logger.warning(f"Invalid credentials for username: {username}")
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            Profile.objects.create(user=user)
            token, created = Token.objects.get_or_create(user=user)
            logger.info(f"User registered: {user.username}, token: {token.key}")
            return Response({'token': token.key, 'username': user.username}, status=status.HTTP_201_CREATED)
        logger.warning(f"Registration failed: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            users = User.objects.exclude(id=request.user.id).select_related('profile')
            serializer = UserSerializer(users, many=True)
            logger.info(f"User list fetched by {request.user.username}")
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error fetching user list: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class AddFriendView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        friend_username = request.data.get('friend_username')
        try:
            friend = User.objects.get(username=friend_username)
            if friend == request.user:
                logger.warning(f"{request.user.username} attempted to add self as friend")
                return Response({'error': 'Cannot add yourself as a friend'}, status=status.HTTP_400_BAD_REQUEST)
            if Friend.objects.filter(user=request.user, friend=friend).exists():
                logger.warning(f"{request.user.username} already friends with {friend_username}")
                return Response({'error': 'Already friends'}, status=status.HTTP_400_BAD_REQUEST)
            if FriendRequest.objects.filter(from_user=request.user, to_user=friend, status='pending').exists():
                logger.warning(f"Friend request already sent to {friend_username}")
                return Response({'error': 'Friend request already sent'}, status=status.HTTP_400_BAD_REQUEST)
            FriendRequest.objects.create(from_user=request.user, to_user=friend, status='pending')
            logger.info(f"Friend request sent from {request.user.username} to {friend_username}")
            return Response({'message': 'Friend request sent'}, status=status.HTTP_201_CREATED)
        except User.DoesNotExist:
            logger.warning(f"Friend not found: {friend_username}")
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error sending friend request: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class MessageListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, friend_username):
        try:
            messages = Message.objects.filter(
                (models.Q(sender=request.user) & models.Q(receiver_username=friend_username)) |
                (models.Q(sender__username=friend_username) & models.Q(receiver_username=request.user.username))
            ).order_by('timestamp').select_related('sender__profile')
            serializer = MessageSerializer(messages, many=True)
            logger.info(f"Messages fetched for {request.user.username} with {friend_username}")
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error fetching messages: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class GetProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = Profile.objects.get(user=request.user)
            serializer = GetProfileSerializer(profile, context={'request': request})
            logger.info(f"Profile fetched for {request.user.username}")
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Profile.DoesNotExist:
            logger.warning(f"Profile not found for {request.user.username}")
            return Response({'error': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error fetching profile: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class PutProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        try:
            profile = Profile.objects.get(user=request.user)
            serializer = PutProfileSerializer(profile, data=request.data, context={'request': request})
            if serializer.is_valid():
                serializer.save()
                logger.info(f"Profile updated for {request.user.username}")
                return Response(serializer.data, status=status.HTTP_200_OK)
            logger.warning(f"Profile update failed for {request.user.username}: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Profile.DoesNotExist:
            logger.warning(f"Profile not found for {request.user.username}")
            return Response({'error': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error updating profile: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class FriendRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            friend_request_id = request.data.get('friend_request_id')
            action = request.data.get('action')  # 'accept' or 'reject'
            friend_request = FriendRequest.objects.get(id=friend_request_id, to_user=request.user)
            if action == 'accept':
                Friend.objects.get_or_create(user=request.user, friend=friend_request.from_user)
                Friend.objects.get_or_create(user=friend_request.from_user, friend=request.user)
                friend_request.status = 'accepted'
                friend_request.save()
                logger.info(f"Friend request accepted by {request.user.username} from {friend_request.from_user.username}")
                return Response({'message': 'Friend request accepted'}, status=status.HTTP_200_OK)
            elif action == 'reject':
                friend_request.status = 'rejected'
                friend_request.save()
                logger.info(f"Friend request rejected by {request.user.username} from {friend_request.from_user.username}")
                return Response({'message': 'Friend request rejected'}, status=status.HTTP_200_OK)
            else:
                logger.warning(f"Invalid action {action} for friend request {friend_request_id}")
                return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)
        except FriendRequest.DoesNotExist:
            logger.warning(f"Friend request {friend_request_id} not found for {request.user.username}")
            return Response({'error': 'Friend request not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error processing friend request: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ListFriendsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            friends = Friend.objects.filter(user=request.user).select_related('friend__profile')
            serializer = FriendSerializer(friends, many=True)
            logger.info(f"Friends listed for {request.user.username}")
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error listing friends: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ListFriendRequestsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            friend_requests = FriendRequest.objects.filter(to_user=request.user, status='pending').select_related('from_user')
            data = [
                {
                    'id': fr.id,
                    'from_username': fr.from_user.username,
                    'created_at': fr.created_at
                } for fr in friend_requests
            ]
            logger.info(f"Friend requests listed for {request.user.username}")
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error listing friend requests: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_424_FAILED_DEPENDENCY)