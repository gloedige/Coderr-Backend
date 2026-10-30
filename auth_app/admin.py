# Third-party
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

# Local imports
from .models import User


@admin.register(User)
class CoderrUserAdmin(UserAdmin):
    """Admin for users with the Coderr account type and email fields."""

    fieldsets = UserAdmin.fieldsets + (
        ('Coderr account', {'fields': ('type',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Coderr account', {'fields': ('email', 'type')}),
    )