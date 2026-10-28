from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Profile, User


@admin.register(User)
class CoderrUserAdmin(UserAdmin):
    """Admin for users with the Coderr account type and email fields."""

    fieldsets = UserAdmin.fieldsets + (
        ('Coderr account', {'fields': ('type',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Coderr account', {'fields': ('email', 'type')}),
    )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """Admin for profiles with search by user and location."""

    list_display = ('user', 'location', 'created_at', 'uploaded_at')
    search_fields = ('user__username', 'user__email', 'location')
