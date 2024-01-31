from django.urls import path
from . import views

urlpatterns = [
    path('slates/', views.get_slates, name='slates'),
    path('add-slate/', views.add_slate, name='add-slate'),
    path('api/unauthenticated-slate-info/<int:slate_id>', views.get_unauthenticated_slate_info, name='unauthenticated-slate-info'),
    path('api/authenticated-optimize/', views.authenticated_optimize, name='authenticated-optomize'),
    path('api/unauthenticated-optimize/', views.unauthenticated_optimize, name='unauthenticated-optomize'),
    path('api/authenticated-slate-info/<int:slate_id>', views.get_authenticated_slate_info, name='authenticated-slate-info'),
]
