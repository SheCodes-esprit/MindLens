from django.contrib.auth.tokens import PasswordResetTokenGenerator
from six import text_type
import random
import string
from datetime import datetime, timedelta
from django.utils import timezone

class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return text_type(user.pk) + text_type(timestamp) + text_type(user.is_email_verified)

email_verification_token = EmailVerificationTokenGenerator()
def generate_otp():
    """Generate a 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))

def is_otp_valid(otp_created_at, expiry_minutes=5):
    """Check if OTP is still valid (default 5 minutes)"""
    if not otp_created_at:
        return False
    expiry_time = otp_created_at + timedelta(minutes=expiry_minutes)
    return timezone.now() < expiry_time