from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from django.db.models import Q
from .models import Friend, FriendRequest, Message, Profile
from .serializers import (
    RegisterSerializer, LoginSerializer, UserListSerializer,
    FriendSerializer, FriendRequestSerializer, FriendRequestActionSerializer,
    MessageSerializer, MessageCountSerializer, GetProfileSerializer, PutProfileSerializer,
    FriendCountSerializer, GlobalMessageCountSerializer 
)
import logging

logger = logging.getLogger(__name__)


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user, token = serializer.create(serializer.validated_data)
            return Response({
                'user': {
                    'username': user.username,
                    'email': user.email,
                    'location': user.profile.location,
                    'picture': user.profile.picture.url if user.profile.picture else None
                },
                'token': token
            }, status=status.HTTP_201_CREATED)
        logger.error(f"Registration failed: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                'user': {'username': user.username, 'email': user.email},
                'token': token.key
            }, status=status.HTTP_200_OK)
        return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class UserListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        search = request.query_params.get('search', '')
        users = User.objects.filter(
            Q(username__icontains=search) | Q(email__icontains=search)
        ).exclude(id=request.user.id)
        serializer = UserListSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class ListFriendsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        friends = Friend.objects.filter(user=request.user)
        serializer = FriendSerializer(friends, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

class AddFriendView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        to_username = request.data.get('to_username')
        if not to_username:
            return Response({'error': 'to_username is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            to_user = User.objects.get(username=to_username)
            if to_user == request.user:
                return Response({'error': 'Cannot send friend request to yourself'}, status=status.HTTP_400_BAD_REQUEST)
            if Friend.objects.filter(user=request.user, friend=to_user).exists():
                return Response({'error': 'Already friends'}, status=status.HTTP_400_BAD_REQUEST)
            if FriendRequest.objects.filter(from_user=request.user, to_user=to_user, status='pending').exists():
                return Response({'error': 'Friend request already sent'}, status=status.HTTP_400_BAD_REQUEST)
            friend_request = FriendRequest.objects.create(from_user=request.user, to_user=to_user, status='pending')
            serializer = FriendRequestSerializer(friend_request, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

class ListFriendRequestsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        request_type = request.query_params.get('type', 'received')
        if request_type == 'sent':
            requests = FriendRequest.objects.filter(from_user=request.user)
        else:
            requests = FriendRequest.objects.filter(to_user=request.user)
        serializer = FriendRequestSerializer(requests, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

class FriendRequestActionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = FriendRequestActionSerializer(data=request.data)
        if serializer.is_valid():
            request_id = serializer.validated_data['request_id']
            action = serializer.validated_data['status']
            try:
                friend_request = FriendRequest.objects.get(id=request_id, to_user=request.user)
                if friend_request.status != 'pending':
                    return Response({'error': 'Request already processed'}, status=status.HTTP_400_BAD_REQUEST)
                friend_request.status = action
                friend_request.save()
                if action == 'accepted':
                    Friend.objects.create(user=friend_request.to_user, friend=friend_request.from_user)
                    Friend.objects.create(user=friend_request.from_user, friend=friend_request.to_user)
                return Response({'message': f'Request {action}'}, status=status.HTTP_200_OK)
            except FriendRequest.DoesNotExist:
                return Response({'error': 'Friend request not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MessageListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, friend_username):
        try:
            friend = User.objects.get(username=friend_username)
            messages = Message.objects.filter(
                Q(sender=request.user, receiver_username=friend.username) | 
                Q(sender=friend, receiver_username=request.user.username)
            ).order_by('timestamp')
            serializer = MessageSerializer(messages, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

class MessageCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        friends = Friend.objects.filter(user=request.user)
        counts = []
        for friend in friends:
            count = Message.objects.filter(
                Q(sender=friend.friend, receiver_username=request.user.username) | 
                Q(sender=request.user, receiver_username=friend.friend.username)
            ).count()
            counts.append({'username': friend.friend.username, 'count': count})
        serializer = MessageCountSerializer(counts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class GetProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = Profile.objects.select_related('user').get(user=request.user)
            serializer = GetProfileSerializer(profile, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Profile.DoesNotExist:
            return Response(
                {'error': 'Profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )

class PutProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        try:
            profile = Profile.objects.get(user=request.user)
            serializer = PutProfileSerializer(profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Profile.DoesNotExist:
            return Response({'error': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)


# === NEW VIEWS ADDED BELOW ===

class FriendCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = Friend.objects.filter(user=request.user).count()
        serializer = FriendCountSerializer({'count': count})
        return Response(serializer.data, status=status.HTTP_200_OK)


class GlobalMessageCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sent = Message.objects.filter(sender=request.user).count()
        received = Message.objects.filter(receiver_username=request.user.username).count()
        total = sent + received
        serializer = GlobalMessageCountSerializer({'count': total})
        return Response(serializer.data, status=status.HTTP_200_OK)