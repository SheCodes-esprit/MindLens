from django.conf import settings
from django.db import models

class VisualEntry(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    type = models.CharField(max_length=10, choices=[('image', 'Image'), ('video', 'Video')])
    media_url = models.FileField(upload_to='visual_entries/')
    caption = models.TextField(blank=True)
    ai_description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class VisualInsight(models.Model):
    visual_entry = models.ForeignKey(VisualEntry, on_delete=models.CASCADE, related_name='insights')
    detected_objects = models.JSONField(default=list)
    dominant_colors = models.JSONField(default=list)
    emotion_detected = models.CharField(max_length=50, blank=True)
    tags_generated = models.JSONField(default=list)
    ai_confidence = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)