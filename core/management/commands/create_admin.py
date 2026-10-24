from getpass import getpass
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = 'Create the initial owner using an email login and a securely prompted password.'

    def add_arguments(self, parser):
        parser.add_argument('--email', help='Owner email. Password is never accepted as a command-line argument.')

    def handle(self, *args, **options):
        email = (options['email'] or input('Owner email: ')).strip().casefold()
        try:
            validate_email(email)
        except ValidationError:
            raise CommandError('Enter a valid email address.')
        if len(email) > 150:
            raise CommandError('Email must be 150 characters or shorter.')
        User = get_user_model()
        if User.objects.filter(username=email).exists():
            raise CommandError('That account already exists. No changes were made.')
        password = getpass('Password (12+ characters; typing is hidden): ')
        if password != getpass('Confirm password: '):
            raise CommandError('Passwords do not match.')
        user = User(username=email, email=email, is_staff=True, is_superuser=True)
        try:
            validate_password(password, user)
        except ValidationError as exc:
            raise CommandError('; '.join(exc.messages))
        user.set_password(password)
        user.save()
        self.stdout.write(self.style.SUCCESS('Owner created. Open /admin/, sign in, and enroll your authenticator before accessing the dashboard.'))
