from django import forms
from .models import VisualEntry

class VisualEntryForm(forms.ModelForm):
    class Meta:
        model = VisualEntry
        fields = ['type', 'media_url', 'caption']
        widgets = {
            'type': forms.Select(attrs={'class': 'form-control'}),
            'caption': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }