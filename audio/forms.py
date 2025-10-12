from django import forms
from .models import AudioEntry

class AudioEntryForm(forms.ModelForm):
    class Meta:
        model = AudioEntry
        fields = ['title', 'audio_url']  # User will be set in view