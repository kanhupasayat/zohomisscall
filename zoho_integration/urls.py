from django.urls import path
from .views import check_numbers_view

urlpatterns = [
    path("check-numbers/", check_numbers_view, name="check_numbers"),
]
