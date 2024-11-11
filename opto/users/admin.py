from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'username', 'first_name',
                    'last_name', 'is_staff', 'is_confirmed')

    def has_delete_permission(self, request, obj=None):
        # Allow deletion only if the user is a superuser
        return request.user.is_superuser


admin.site.register(CustomUser, CustomUserAdmin)
