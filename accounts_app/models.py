from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q


class User(AbstractUser):
    """Account with a unique email and a customer or business role."""

    class UserType(models.TextChoices):
        """Allowed account roles."""

        CUSTOMER = 'customer', 'Customer'
        BUSINESS = 'business', 'Business'

    email = models.EmailField(unique=True)
    type = models.CharField(max_length=10, choices=UserType.choices)
    REQUIRED_FIELDS = ['email', 'type']

    class Meta:
        """Restrict `type` to the defined roles."""

        constraints = [
            models.CheckConstraint(
                condition=Q(type__in=['customer', 'business']),
                name='accounts_user_type_valid',
            ),
        ]

    def save(self, *args, **kwargs):
        """Trim the username, normalize the email, and save the user."""
        self.username = self.username.strip()
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)


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

    def __str__(self):
        """Return the owning username followed by 'profile'."""
        return f'{self.user.username} profile'
