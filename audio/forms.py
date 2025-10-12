from django import forms
from .models import AudioEntry

class AudioEntryForm(forms.ModelForm):
    recorded_audio = forms.CharField(widget=forms.HiddenInput(), required=False)  # For base64 encoded audio

    class Meta:
        model = AudioEntry
        fields = ['title', 'audio_url', 'recorded_audio']