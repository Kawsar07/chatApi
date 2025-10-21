from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Profile, Friend
from knox.models import AuthToken
import redis

redis_client = redis.Redis(host='127.0.0.1', port=6379, db=0)

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['picture', 'location']

class GetProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username')
    email = serializers.EmailField(source='user.email')

    class Meta:
        model = Profile
        fields = ['username', 'email', 'picture', 'location']

class PutProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', required=False)
    email = serializers.EmailField(source='user.email', required=False)

    class Meta:
        model = Profile
        fields = ['username', 'email', 'picture', 'location']

    def validate_email(self, value):
        user = self.context['request'].user
        if User.objects.exclude(pk=user.pk).filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value

    def validate_username(self, value):
        user = self.context['request'].user
        if User.objects.exclude(pk=user.pk).filter(username=value).exists():
            raise serializers.ValidationError("Username already exists")
        return value

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        user = instance.user
        if 'username' in user_data:
            user.username = user_data['username']
        if 'email' in user_data:
            user.email = user_data['email']
        user.save()
        instance.picture = validated_data.get('picture', instance.picture)
        instance.location = validated_data.get('location', instance.location)
        instance.save()
        return instance

class FriendSerializer(serializers.ModelSerializer):
    friend_username = serializers.CharField(source='friend.username')
    friend_email = serializers.EmailField(source='friend.email')
    friend_picture = serializers.SerializerMethodField()
    friend_location = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = Friend
        fields = ['friend_username', 'friend_email', 'friend_picture', 'friend_location', 'is_active']

    def get_friend_picture(self, obj):
        try:
            profile = Profile.objects.get(user=obj.friend)
            return profile.picture.url if profile.picture else ''
        except Profile.DoesNotExist:
            return ''

    def get_friend_location(self, obj):
        try:
            profile = Profile.objects.get(user=obj.friend)
            return profile.location
        except Profile.DoesNotExist:
            return ''

    def get_is_active(self, obj):
        return redis_client.exists(f'user:{obj.friend.username}:active')

class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    picture = serializers.ImageField(required=False)
    location = serializers.CharField(max_length=100, required=False)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        Profile.objects.create(
            user=user,
            picture=validated_data.get('picture'),
            location=validated_data.get('location', '')
        )
        token = AuthToken.objects.create(user)[1]
        return user, token

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = User.objects.filter(email=data['email']).first()
        if user and user.check_password(data['password']):
            return user
        raise serializers.ValidationError("Invalid credentials")