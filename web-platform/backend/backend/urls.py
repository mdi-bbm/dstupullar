from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from network.views import RegisterView

urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/", include('network.urls')), 
    path('api/register/', RegisterView.as_view(), name='register'),
    path("api/token_9fqmnqe010opnsvq9ql/", TokenObtainPairView.as_view(), name="token"),
    path("api/refresh_token_gn240202ns301f1/", TokenRefreshView.as_view(), name="refresh_token"),
    
]  + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)