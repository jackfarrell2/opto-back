from django.urls import path
from . import views

urlpatterns = [
    path('slates/', views.get_slates, name='slates'),
    path('add-slate/', views.add_slate, name='add-slate'),
    path('api/unauthenticated-slate-info/<int:slate_id>',
         views.get_unauthenticated_slate_info, name='unauthenticated-slate-info'),
    path('api/authenticated-optimize/', views.authenticated_optimize,
         name='authenticated-optomize'),
    path('api/unauthenticated-optimize/', views.unauthenticated_optimize,
         name='unauthenticated-optomize'),
    path('api/authenticated-slate-info/<int:slate_id>',
         views.get_authenticated_slate_info, name='authenticated-slate-info'),
    path('api/user-opto-settings/', views.user_opto_settings,
         name='user-opto-settings'),
    path('api/player-settings/', views.player_settings, name='player-settings'),
    path('api/upload-projections/', views.upload_projections,
         name='upload-projections'),
    path('api/remove-projections/', views.remove_projections,
         name='remove-projections'),
    path('api/remove-optimizations/', views.remove_optimizations,
         name='remove-optimizations'),
    path('api/cancel-optimization/', views.cancel_optimization,
         name='cancel-optimization'),
]
