from django.urls import path
from .views import admin_audio_history, admin_audio_history_pdf

urlpatterns = [
    path('history/', admin_audio_history, name='admin_audio_history'),
    path('audio-history/pdf/', admin_audio_history_pdf, name='admin_audio_history_pdf'),
]
