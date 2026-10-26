from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class UserType(models.TextChoices):
        CUSTOMER = 'customer', 'Customer'
        BUSINESS = 'business', 'Business'

    email = models.EmailField(unique=True)
    type = models.CharField(max_length=10, choices=UserType.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                models.functions.Lower('username'),
                name='accounts_user_username_ci_unique',
            ),
            models.UniqueConstraint(
                models.functions.Lower('email'),
                name='accounts_user_email_ci_unique',
            ),
        ]


class Profile(models.Model):
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
        return f'{self.user.username} profile'
