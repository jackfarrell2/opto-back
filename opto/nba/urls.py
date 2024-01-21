from django.urls import path
from . import views

urlpatterns = [
    path('slates/', views.get_slates)
]