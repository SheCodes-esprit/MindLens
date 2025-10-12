from django.urls import path
from .views import audio_list, audio_create, audio_detail, audio_delete

urlpatterns = [
    path('audio/', audio_list, name='audio_list'),
    path('audio/create/', audio_create, name='audio_create'),
    path('audio/<int:pk>/', audio_detail, name='audio_detail'),
    path('audio/<int:pk>/delete/', audio_delete, name='audio_delete'),
]