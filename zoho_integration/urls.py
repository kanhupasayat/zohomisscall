from django.urls import path
from . import views

urlpatterns = [
    path('fetch-zoho/', views.fetch_zoho_data_stream, name='fetch_zoho_data_stream'),
    
]