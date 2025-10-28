from django.urls import path
from . import views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('api/login/', views.LoginView.as_view(), name='login'),
    path('api/register/', views.RegisterView.as_view(), name='register'),
    path('api/users/', views.UserListView.as_view(), name='user-list'),
    path('api/add-friend/', views.AddFriendView.as_view(), name='add-friend'),
    path('api/messages/<str:friend_username>/', views.MessageListView.as_view(), name='message-list'),
    path('api/profile/', views.GetProfileView.as_view(), name='get-profile'),
    path('api/profile/update/', views.PutProfileView.as_view(), name='put-profile'),
    path('api/friend-requests/', views.ListFriendRequestsView.as_view(), name='list-friend-requests'),
    path('api/friend-request/action/', views.FriendRequestActionView.as_view(), name='friend-request-action'),
    path('api/friends/', views.ListFriendsView.as_view(), name='list-friends'),
    path('api/messages/count/', views.MessageCountView.as_view(), name='message-count'),
    path('api/friend-count/', views.FriendCountView.as_view(), name='friend-count'),
    path('api/message-count/', views.GlobalMessageCountView.as_view(), name='global-message-count'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)