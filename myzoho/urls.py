from django.contrib import admin
from django.urls import path, include  # include import karna zaruri hai

urlpatterns = [
    path('admin/', admin.site.urls),
    path('zoho/', include('zoho_integration.urls')),  # <--- app URLs include
]
