from django.urls import path
from .views import admin_audio_history

urlpatterns = [
    path('history/', admin_audio_history, name='admin_audio_history'),
]