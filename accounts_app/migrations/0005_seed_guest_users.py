import secrets

from django.contrib.auth.hashers import make_password
from django.db import migrations


GUEST_USERS = (
    ('guest_customer', 'guest_customer@example.com', 'customer'),
    ('guest_business', 'guest_business@example.com', 'business'),
)
GUEST_PASSWORD = 'guest1234'


def seed_guest_users(apps, schema_editor):
    """Create the registration-equivalent guest accounts, profiles, and tokens."""
    User = apps.get_model('accounts_app', 'User')
    Profile = apps.get_model('accounts_app', 'Profile')
    Token = apps.get_model('authtoken', 'Token')
    database = schema_editor.connection.alias

    create_guest_users(database, User, Profile, Token)

def create_guest_users(database, User, Profile, Token):
    """Create the registration-equivalent guest accounts, profiles, and tokens."""
    for username, email, user_type in GUEST_USERS:
        user, created = User.objects.using(database).get_or_create(
            username=username,
            defaults={
                'email': email,
                'type': user_type,
                'password': make_password(GUEST_PASSWORD),
            },
        )
        Profile.objects.using(database).get_or_create(user_id=user.pk)
        Token.objects.using(database).get_or_create(
            user_id=user.pk,
            defaults={'key': secrets.token_hex(20)},
        )

class Migration(migrations.Migration):
    dependencies = [
        ('accounts_app', '0004_remove_user_accounts_user_username_ci_unique'),
        ('authtoken', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_guest_users, migrations.RunPython.noop),
    ]