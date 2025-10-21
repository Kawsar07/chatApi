from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions  # Add permissions import
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer, GetProfileSerializer, PutProfileSerializer, FriendSerializer
from knox.models import AuthToken
from django.contrib.auth import login
from django.shortcuts import render
from .models import Profile, Friend
from django.contrib.auth.models import User
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]  # Ensure no authentication required

    @swagger_auto_schema(
        request_body=RegisterSerializer,
        responses={201: UserSerializer, 400: 'Bad Request'}
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user, token = serializer.create(serializer.validated_data)
            return Response({
                'user': UserSerializer(user).data,
                'token': token,
                'message': 'Registration successful'
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]  # Ensure no authentication required

    @swagger_auto_schema(
        request_body=LoginSerializer,
        responses={200: UserSerializer, 400: 'Bad Request'}
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data
            login(request, user)
            token = AuthToken.objects.create(user)[1]
            return Response({
                'user': UserSerializer(user).data,
                'token': token,
                'message': 'Login successful'
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class GetProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(responses={200: GetProfileSerializer, 404: 'Not Found'})
    def get(self, request):
        try:
            profile = Profile.objects.get(user=request.user)
            serializer = GetProfileSerializer(profile)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Profile.DoesNotExist:
            return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)

class PutProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        request_body=PutProfileSerializer,
        responses={200: PutProfileSerializer, 400: 'Bad Request', 404: 'Not Found'}
    )
    def put(self, request):
        try:
            profile = Profile.objects.get(user=request.user)
            serializer = PutProfileSerializer(profile, data=request.data, context={'request': request})
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Profile.DoesNotExist:
            return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)

class AddFriendView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={'friend_username': openapi.Schema(type=openapi.TYPE_STRING)}
        ),
        responses={201: 'Created', 400: 'Bad Request', 404: 'Not Found'}
    )
    def post(self, request):
        friend_username = request.data.get('friend_username')
        try:
            friend = User.objects.get(username=friend_username)
            if friend == request.user:
                return Response({"error": "Cannot add yourself as a friend"}, status=status.HTTP_400_BAD_REQUEST)
            Friend.objects.get_or_create(user=request.user, friend=friend)
            return Response({"message": f"{friend_username} added as friend"}, status=status.HTTP_201_CREATED)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

class ListFriendsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(responses={200: FriendSerializer(many=True)})
    def get(self, request):
        friends = Friend.objects.filter(user=request.user)
        serializer = FriendSerializer(friends, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

def chat_room(request):
    return render(request, 'chat_room.html')