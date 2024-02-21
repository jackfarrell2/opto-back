from django.urls import re_path, path
from . import views

urlpatterns = [
    re_path('sign-in', views.login),
    re_path('signup', views.signup),
    re_path('test_token', views.test_token),
    path('activate/<str:token>', views.confirm_email),
]

