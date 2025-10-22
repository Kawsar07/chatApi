from django.urls import path
from . import views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('addfriend/', views.AddFriendView.as_view(), name='add_friend'),
    path('messages/<str:friend_username>/', views.MessageListView.as_view(), name='messages'),
    path('getprofile/', views.GetProfileView.as_view(), name='get_profile'),
    path('putprofile/', views.PutProfileView.as_view(), name='put_profile'),
    path('listfriends/', views.ListFriendsView.as_view(), name='list_friends'),
    path('friendrequest/', views.FriendRequestView.as_view(), name='friend_request'),
    path('listfriendrequests/', views.ListFriendRequestsView.as_view(), name='list_friend_requests'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)