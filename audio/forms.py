from django import forms
from .models import AudioEntry

class AudioEntryForm(forms.ModelForm):
    recorded_audio = forms.CharField(widget=forms.HiddenInput(), required=False)
    
    # Customize the audio_url field
    audio_url = forms.FileField(
        label="Upload Audio File (Optional)",
        widget=forms.FileInput(attrs={
            'accept': 'audio/*',
            'class': 'custom-file-input'
        }),
        required=False
    )

    class Meta:
        model = AudioEntry
        fields = ['title', 'audio_url', 'recorded_audio']
        
    # You can also customize the title field if needed
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter a title for your audio entry'
        })