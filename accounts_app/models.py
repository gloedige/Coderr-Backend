from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q


class User(AbstractUser):
    class UserType(models.TextChoices):
        CUSTOMER = 'customer', 'Customer'
        BUSINESS = 'business', 'Business'

    email = models.EmailField(unique=True)
    type = models.CharField(max_length=10, choices=UserType.choices)
    REQUIRED_FIELDS = ['email', 'type']

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(type__in=['customer', 'business']),
                name='accounts_user_type_valid',
            ),
            models.UniqueConstraint(
                models.functions.Collate('username', 'NOCASE'),
                name='accounts_user_username_ci_unique',
            ),
        ]

    def save(self, *args, **kwargs):
        self.username = self.username.strip()
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)


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
