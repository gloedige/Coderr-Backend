# Third-party
from django.db import models

# Local imports
from auth_app.models import User

class Profile(models.Model):
    """Profile data shared by customer and business users."""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profile'
    )
    first_name = models.CharField(max_length=150, blank=True, default='')
    last_name = models.CharField(max_length=150, blank=True, default='')
    file = models.FileField(upload_to='uploads/', blank=True, null=True)
    uploaded_at = models.DateTimeField(blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, default='')
    tel = models.CharField(max_length=50, blank=True, default='')
    description = models.CharField(max_length=500, blank=True, default='')
    working_hours = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Order profiles by owner and set readable admin names."""

        ordering = ('user_id',)
        verbose_name = 'profile'
        verbose_name_plural = 'profiles'

    def __str__(self):
        """Return the owning username followed by 'profile'."""
        return f'{self.user.username} profile'
