from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.db.models import Q
from .models import Profile, Friend, Message, FriendRequest
from .serializers import (
    UserSerializer, UserListSerializer, ProfileSerializer, GetProfileSerializer,
    PutProfileSerializer, FriendSerializer, MessageSerializer, RegisterSerializer,
    LoginSerializer, FriendRequestSerializer, FriendRequestActionSerializer
)
import logging

logger = logging.getLogger(__name__)  # For debugging

class RegisterView(generics.CreateAPIView):
    """
    POST: Register a new user.
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user, token_key = serializer.save()
            return Response({
                'user': UserSerializer(user).data,
                'token': token_key
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    """
    POST: Login a user by email/password, return token.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                'user': UserSerializer(user).data,
                'token': token.key
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserListView(generics.ListAPIView):
    """
    GET: List all users (for friend search).
    Query param: ?search=<query> to filter by username (case-insensitive partial match).
    """
    queryset = User.objects.all()
    serializer_class = UserListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.query_params.get('search', None)
        if search_query:
            queryset = queryset.filter(Q(username__icontains=search_query) | Q(first_name__icontains=search_query) | Q(last_name__icontains=search_query) | Q(email__icontains=search_query))
        # Optionally exclude self
        return queryset.exclude(id=self.request.user.id).distinct()

class AddFriendView(APIView):
    """
    POST: Send a friend request to another user by username.
    Expects: {"to_username": "target_username"}
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        to_username = request.data.get('to_username')
        if not to_username:
            return Response({"error": "to_username is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            to_user = User.objects.get(username=to_username)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        
        from_user = request.user
        
        # Check if already friends
        if Friend.objects.filter(user=from_user, friend=to_user).exists():
            return Response({"error": "Already friends"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if request already exists
        if FriendRequest.objects.filter(from_user=from_user, to_user=to_user).exists():
            return Response({"error": "Friend request already sent"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create pending request
        friend_request = FriendRequest.objects.create(
            from_user=from_user,
            to_user=to_user,
            status='pending'
        )
        
        serializer = FriendRequestSerializer(friend_request)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class MessageListView(generics.ListCreateAPIView):
    """
    GET: List messages with a friend.
    POST: Send a new message.
    """
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        friend_username = self.kwargs['friend_username']
        return Message.objects.filter(
            sender=self.request.user,
            receiver_username=friend_username
        ) | Message.objects.filter(
            sender__username=friend_username,
            receiver_username=self.request.user.username
        ).order_by('timestamp')

    def perform_create(self, serializer):
        friend_username = self.kwargs['friend_username']
        serializer.save(sender=self.request.user, receiver_username=friend_username)

class GetProfileView(generics.RetrieveAPIView):
    """
    GET: Get current user's profile.
    """
    serializer_class = GetProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        profile, created = Profile.objects.get_or_create(user=self.request.user)
        return profile

class PutProfileView(generics.UpdateAPIView):
    """
    PUT/PATCH: Update current user's profile.
    """
    serializer_class = PutProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        profile, created = Profile.objects.get_or_create(user=self.request.user)
        return profile

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

class ListFriendRequestsView(generics.ListAPIView):
    """
    GET: List received or sent friend requests for the current user.
    Query params: ?type=received (default) or ?type=sent
    """
    serializer_class = FriendRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        request_type = self.request.query_params.get('type', 'received')
        
        if request_type == 'received':
            return FriendRequest.objects.filter(to_user=user, status='pending')
        elif request_type == 'sent':
            return FriendRequest.objects.filter(from_user=user)
        else:
            return FriendRequest.objects.none()  # Invalid type

class FriendRequestView(APIView):
    """
    POST/PATCH: Accept or reject a friend request by ID.
    Expects: {"request_id": 1, "status": "accepted"} or {"status": "rejected"}
    Supports both POST and PATCH.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        return self._handle_action(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):  # Added for PATCH support
        return self._handle_action(request, *args, **kwargs)

    def _handle_action(self, request, *args, **kwargs):
        request_id = request.data.get('request_id')
        if not request_id:
            return Response({"error": "request_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            request_id = int(request_id)  # Ensure int, handle conversion error
        except (ValueError, TypeError):
            return Response({"error": "Invalid request_id format (must be integer)"}, status=status.HTTP_400_BAD_REQUEST)
        
        friend_request = get_object_or_404(FriendRequest, id=request_id, to_user=request.user)
        
        if friend_request.status != 'pending':
            return Response({"error": "Can only act on pending requests"}, status=status.HTTP_400_BAD_REQUEST)
        
        logger.debug(f"Processing request {request_id} with status {request.data.get('status')}")  # Debug log
        
        serializer = FriendRequestActionSerializer(data=request.data)
        if serializer.is_valid():
            status = serializer.validated_data['status']
            
            logger.debug(f"Valid status: {status}")  # Debug
            
            if status == 'accepted':
                logger.debug("Creating friend records")  # Debug
                Friend.objects.get_or_create(user=friend_request.to_user, friend=friend_request.from_user)
                Friend.objects.get_or_create(user=friend_request.from_user, friend=friend_request.to_user)
            
            friend_request.status = status
            friend_request.save()
            logger.debug("Saved request status")  # Debug
            
            try:
                # Try to serialize full data
                updated_serializer = FriendRequestSerializer(friend_request)
                logger.debug(f"Serialized data: {updated_serializer.data}")  # Debug
                return Response(updated_serializer.data, status=status.HTTP_200_OK)
            except Exception as e:
                # Fallback if serialization fails (e.g., AttributeError)
                logger.error(f"Serialization error: {e}")
                return Response({
                    "success": True,
                    "id": friend_request.id,
                    "status": friend_request.status,
                    "message": f"Request {status} successfully"
                }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ListFriendsView(generics.ListAPIView):
    """
    GET: List current user's friends.
    """
    serializer_class = FriendSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Friend.objects.filter(user=self.request.user)