from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from chat.views import RegisterView, LoginView, GetProfileView, PutProfileView, AddFriendView, ListFriendsView
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="Chat App API",
        default_version='v1',
        description="API for chat application with user management and friends",
    ),
    public=True,
    permission_classes=[permissions.AllowAny],  # Ensure no authentication required
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/register/', RegisterView.as_view(), name='register'),
    path('api/login/', LoginView.as_view(), name='login'),
    path('api/getprofile/', GetProfileView.as_view(), name='get_profile'),
    path('api/putprofile/', PutProfileView.as_view(), name='put_profile'),
    path('api/addfriend/', AddFriendView.as_view(), name='add_friend'),
    path('api/listfriends/', ListFriendsView.as_view(), name='list_friends'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('chat/', include('chat.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)