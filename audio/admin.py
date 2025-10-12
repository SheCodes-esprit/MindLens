from django.contrib import admin
from .models import AudioEntry, AudioEmotionAnalysis

@admin.register(AudioEntry)
class AudioEntryAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'duration', 'created_at')
    list_filter = ('user', 'created_at')
    search_fields = ('title', 'user__username')

@admin.register(AudioEmotionAnalysis)
class AudioEmotionAnalysisAdmin(admin.ModelAdmin):
    list_display = ('audio_entry', 'detected_emotion', 'intensity', 'created_at')
    list_filter = ('detected_emotion', 'created_at')
    search_fields = ('audio_entry__title', 'detected_emotion')