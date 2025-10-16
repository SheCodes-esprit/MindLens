from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator, EmailValidator
from django.core.exceptions import ValidationError
import re
from django.utils import timezone
from django.contrib.sessions.models import Session

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
    
    # Add these fields to your User model:

    is_2fa_enabled = models.BooleanField(default=False)
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_created_at = models.DateTimeField(blank=True, null=True)
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


#USER SESSION MODEL
class UserSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    device_type = models.CharField(max_length=50, blank=True)  # Mobile, Desktop, Tablet
    browser = models.CharField(max_length=50, blank=True)
    operating_system = models.CharField(max_length=50, blank=True)
    location = models.CharField(max_length=200, blank=True)  # City, Country
    is_active = models.BooleanField(default=True)
    is_suspicious = models.BooleanField(default=False)
    last_activity = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-last_activity']
        
    def __str__(self):
        return f"{self.user.username} - {self.device_type} - {self.created_at}"
    
    def is_current_session(self, request):
        return self.session_key == request.session.session_key
    
    def get_device_info(self):
        return f"{self.browser} on {self.operating_system}"