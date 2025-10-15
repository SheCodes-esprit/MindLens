from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator, EmailValidator
from django.core.exceptions import ValidationError
import re

class User(AbstractUser):
    is_email_verified = models.BooleanField(default=False)
    JOURNALIST = 'JOURNALIST'
    ADMIN = 'ADMIN'

    ROLE_CHOICES = [
        (JOURNALIST, 'Journalist'),
        (ADMIN, 'Admin'),
    ]

    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default=JOURNALIST,
        help_text="Role of the user: Journalist or Admin"
    )

    profile_image = models.ImageField(
        upload_to='profile_images/',
        blank=True,
        null=True
    )

    email = models.EmailField(
        unique=True,
        validators=[EmailValidator(message="Enter a valid email address.")],
        error_messages={
            'required': 'Email is required.',
            'unique': 'A user with this email already exists.'
        }
    )

    def clean(self):
        super().clean()

        if not self.username:
            raise ValidationError({'username': 'Username is required.'})

        if self.password:
            pattern = r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[\W_]).{8,}$'
            if not re.match(pattern, self.password):
                raise ValidationError({'password': 'Password must be at least 8 characters and include uppercase, lowercase, number, and special character.'})

    def is_journalist(self):
        return self.role == self.JOURNALIST

    def is_admin(self):
        return self.role == self.ADMIN
