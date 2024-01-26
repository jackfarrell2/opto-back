from django.urls import path
from . import views

urlpatterns = [
    path('slates/', views.get_slates, name='slates'),
    path('add-slate/', views.add_slate, name='add-slate'),
    path('get-slate/<int:slate_id>', views.get_slate, name='get-slate'),
    path('optomize/', views.optomize, name='optomize'),
]
