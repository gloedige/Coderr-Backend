from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """Admin for profiles with search by user and location."""

    list_display = ('user', 'location', 'created_at', 'uploaded_at')
    search_fields = ('user__username', 'user__email', 'location')