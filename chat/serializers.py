from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from .models import Profile, Friend, Message, FriendRequest
import logging

logger = logging.getLogger(__name__)
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['user', 'email', 'location', 'picture']

class GetProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email    = serializers.EmailField(source='user.email', read_only=True)
    location = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    picture  = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ['username', 'email', 'location', 'picture']

    def get_picture(self, obj):
        if not obj.picture:
            return None
        request = self.context.get('request')
        picture_url = obj.picture.url if hasattr(obj.picture, 'url') else str(obj.picture)
        if request:
            return request.build_absolute_uri(picture_url)
        return picture_url

class PutProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Profile
        fields = ['email', 'location', 'picture']

    def validate_email(self, value):
        if value and not value.strip():
            raise serializers.ValidationError("Email cannot be empty")
        return value

    def update(self, instance, validated_data):
        instance.email = validated_data.get('email', instance.email)
        instance.location = validated_data.get('location', instance.location)
        if 'picture' in validated_data:
            instance.picture = validated_data['picture']
        instance.save()

        if 'email' in validated_data:
            instance.user.email = validated_data['email']
            instance.user.save()

        return instance

class FriendSerializer(serializers.ModelSerializer):
    friend_username = serializers.CharField(source='friend.username', read_only=True)
    friend_picture = serializers.SerializerMethodField()
    friend_location = serializers.CharField(source='friend.profile.location', read_only=True, allow_null=True)

    class Meta:
        model = Friend
        fields = ['user', 'friend', 'friend_username', 'friend_picture', 'friend_location', 'created_at']

    def get_friend_picture(self, obj):
        try:
            if obj.friend.profile.picture:
                request = self.context.get('request')
                picture_url = obj.friend.profile.picture.url if hasattr(obj.friend.profile.picture, 'url') else obj.friend.profile.picture
                return request.build_absolute_uri(picture_url) if request else picture_url
            return None
        except Profile.DoesNotExist:
            return None

class MessageSerializer(serializers.ModelSerializer):
    sender_picture = serializers.SerializerMethodField()
    receiver_picture = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['sender', 'receiver_username', 'content', 'timestamp', 'sender_picture', 'receiver_picture']

    def get_sender_picture(self, obj):
        try:
            if obj.sender.profile.picture:
                request = self.context.get('request')
                picture_url = obj.sender.profile.picture.url if hasattr(obj.sender.profile.picture, 'url') else obj.sender.profile.picture
                return request.build_absolute_uri(picture_url) if request else picture_url
            return None
        except Profile.DoesNotExist:
            return None

    def get_receiver_picture(self, obj):
        try:
            receiver = User.objects.get(username=obj.receiver_username)
            if receiver.profile.picture:
                request = self.context.get('request')
                picture_url = receiver.profile.picture.url if hasattr(receiver.profile.picture, 'url') else receiver.profile.picture
                return request.build_absolute_uri(picture_url) if request else picture_url
            return None
        except (User.DoesNotExist, Profile.DoesNotExist):
            return None

class MessageCountSerializer(serializers.Serializer):
    username = serializers.CharField()
    count = serializers.IntegerField()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    location = serializers.CharField(max_length=100, required=False, allow_blank=True)
    picture = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'location', 'picture']

    def create(self, validated_data):
        logger.debug(f"Registering user with data: {validated_data}")

        location = validated_data.pop('location', '')
        picture = validated_data.pop('picture', None)

        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )

        profile, created = Profile.objects.get_or_create(user=user)
        profile.location = location
        if picture:
            profile.picture = picture
        profile.email = user.email  # sync
        profile.save()

        token, _ = Token.objects.get_or_create(user=user)
        logger.debug(f"User registered: {user.username}, Token: {token.key}")

        return user, token.key

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    password = serializers.CharField()

    def validate(self, data):
        logger.debug(f"Validating login with data: {data}")
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        if not (username or email):
            raise serializers.ValidationError("Either username or email is required")

        try:
            if email:
                user = User.objects.get(email=email)
                username = user.username
            else:
                user = User.objects.get(username=username)
            user = authenticate(username=username, password=password)
            if user and user.is_active:
                logger.debug(f"User authenticated: {user.username}")
                return user
            logger.error("Authentication failed: Incorrect credentials")
            raise serializers.ValidationError("Incorrect credentials")
        except User.DoesNotExist:
            logger.error(f"User with {'email' if email else 'username'} {email or username} not found")
            raise serializers.ValidationError("Incorrect credentials")

class FriendRequestSerializer(serializers.ModelSerializer):
    from_username = serializers.CharField(source='from_user.username', read_only=True)
    to_username = serializers.CharField(source='to_user.username', read_only=True)
    from_email = serializers.CharField(source='from_user.email', read_only=True)
    to_email = serializers.CharField(source='to_user.email', read_only=True)
    from_picture = serializers.SerializerMethodField()
    to_picture = serializers.SerializerMethodField()

    class Meta:
        model = FriendRequest
        fields = [
            'id', 'from_user', 'to_user', 'from_username', 'to_username',
            'from_email', 'to_email', 'from_picture', 'to_picture',
            'status', 'created_at'
        ]

    def get_from_picture(self, obj):
        try:
            if obj.from_user.profile.picture:
                request = self.context.get('request')
                picture_url = obj.from_user.profile.picture.url if hasattr(obj.from_user.profile.picture, 'url') else obj.from_user.profile.picture
                return request.build_absolute_uri(picture_url) if request else picture_url
            return None
        except Profile.DoesNotExist:
            return None

    def get_to_picture(self, obj):
        try:
            if obj.to_user.profile.picture:
                request = self.context.get('request')
                picture_url = obj.to_user.profile.picture.url if hasattr(obj.to_user.profile.picture, 'url') else obj.to_user.profile.picture
                return request.build_absolute_uri(picture_url) if request else picture_url
            return None
        except Profile.DoesNotExist:
            return None

class FriendRequestActionSerializer(serializers.Serializer):
    request_id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=['accepted', 'rejected'])


class FriendCountSerializer(serializers.Serializer):
    count = serializers.IntegerField(read_only=True)


class GlobalMessageCountSerializer(serializers.Serializer):
    count = serializers.IntegerField(read_only=True)