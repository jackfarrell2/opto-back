from django.urls import re_path, path
from . import views

urlpatterns = [
    re_path('sign-in', views.login),
    re_path('signup', views.signup),
    re_path('test_token', views.test_token),
    path('activate/<str:token>', views.confirm_email),
    path('resend-confirmation', views.resend_confirmation),
    path('reset-password-request', views.reset_password_request),
    path('confirm-password-reset/<str:token>', views.confirm_password_reset),
    path('reset-password', views.reset_password),
]

