from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from .models import UserSession

@receiver(user_logged_in)
def notify_suspicious_login(sender, request, user, **kwargs):
    try:
        session_key = request.session.session_key
        user_session = UserSession.objects.get(session_key=session_key)
        
        if user_session.is_suspicious:
            # Send notification email
            subject = "Suspicious Login Detected - MindLens"
            message = render_to_string("frontoffice/emails/suspicious_login.html", {
                "user": user,
                "session": user_session,
            })
            email_message = EmailMessage(subject, message, to=[user.email])
            email_message.content_subtype = "html"
            email_message.send()
    except UserSession.DoesNotExist:
        pass