from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
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

    def is_journalist(self):
        return self.role == self.JOURNALIST

    def is_admin(self):
        return self.role == self.ADMIN
