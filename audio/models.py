from django.db import models
from users.models import User 

class AudioEntry(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='audio_entries')
    title = models.CharField(max_length=255, blank=True, null=True)
    audio_url = models.FileField(upload_to='audio_entries/', blank=True, null=True)  # For storing audio files
    duration = models.FloatField(blank=True, null=True)  # In seconds
    ai_transcript = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title or 'Untitled'} - {self.user.username}"

class AudioEmotionAnalysis(models.Model):
    audio_entry = models.ForeignKey(AudioEntry, on_delete=models.CASCADE, related_name='emotion_analyses')
    detected_emotion = models.CharField(max_length=100)  # e.g., 'joy', 'sadness', 'stress'
    intensity = models.FloatField()  # e.g., 0.0 to 1.0
    ai_model_version = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.detected_emotion} ({self.intensity}) for {self.audio_entry}"


    def get_dominant_emotion(self):
        """Return the emotion with the highest intensity, or '–'."""
        analysis = self.emotion_analyses.order_by('-intensity').first()
        return analysis.detected_emotion if analysis else '–'

    AudioEntry.dominant_emotion = property(get_dominant_emotion)