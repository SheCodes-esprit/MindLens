from django.utils import timezone
from django.contrib.sessions.models import Session
from .models import UserSession
from user_agents import parse
from ipware import get_client_ip

class SessionTrackingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            session_key = request.session.session_key
            
            if session_key:
                # Get or create user session
                user_session, created = UserSession.objects.get_or_create(
                    session_key=session_key,
                    defaults={
                        'user': request.user,
                    }
                )
                
                if created or not user_session.user:
                    # Parse user agent
                    user_agent = parse(request.META.get('HTTP_USER_AGENT', ''))
                    
                    # Get IP address
                    client_ip, is_routable = get_client_ip(request)
                    
                    # Update session info
                    user_session.user = request.user
                    user_session.ip_address = client_ip
                    user_session.user_agent = str(user_agent)
                    user_session.device_type = self.get_device_type(user_agent)
                    user_session.browser = user_agent.browser.family
                    user_session.operating_system = user_agent.os.family
                    user_session.location = self.get_location(client_ip)
                    user_session.is_suspicious = self.check_suspicious(request.user, client_ip)
                    user_session.save()
                
                # Update last activity
                user_session.last_activity = timezone.now()
                user_session.save(update_fields=['last_activity'])
        
        response = self.get_response(request)
        return response
    
    def get_device_type(self, user_agent):
        if user_agent.is_mobile:
            return 'Mobile'
        elif user_agent.is_tablet:
            return 'Tablet'
        elif user_agent.is_pc:
            return 'Desktop'
        return 'Unknown'
    
    def get_location(self, ip_address):
        try:
            from geolite2 import geolite2
            reader = geolite2.reader()
            match = reader.get(ip_address)
            if match and 'country' in match:
                country = match['country']['names'].get('en', 'Unknown')
                city = match.get('city', {}).get('names', {}).get('en', '')
                return f"{city}, {country}" if city else country
        except:
            pass
        return 'Unknown'
    
    def check_suspicious(self, user, ip_address):
        # Check if IP is from a different country than usual
        recent_sessions = UserSession.objects.filter(
            user=user,
            is_active=True
        ).exclude(ip_address=ip_address)[:5]
        
        if recent_sessions.exists():
            # Simple check: if IP location differs significantly
            current_location = self.get_location(ip_address)
            for session in recent_sessions:
                if session.location != current_location and current_location != 'Unknown':
                    return True
        return False