from django import forms
from .models import WellbeingRecord, RoutineRecommendation

class WellbeingRecordForm(forms.ModelForm):
    class Meta:
        model = WellbeingRecord
        fields = ['mood_score', 'energy_level', 'sleep_hours', 'productivity_score']
        widgets = {
            'mood_score': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 10,
                'placeholder': 'Score from 1 to 10'
            }),
            'energy_level': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 10,
                'placeholder': 'Niveau de 1 à 10'
            }),
            'sleep_hours': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 24,
                'step': 0.5,
                'placeholder': 'Sleep hours'
            }),
            'productivity_score': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 10,
                'placeholder': 'Score from 1 to 10'
            }),
        }
        labels = {
            'mood_score': 'Mood score',
            'energy_level': 'Energy Level',
            'sleep_hours': 'Sleep Hours',
            'productivity_score': 'Productivity Score',
        }

class RoutineRecommendationForm(forms.ModelForm):
    class Meta:
        model = RoutineRecommendation
        fields = ['type', 'description', 'efficiency_score']
        widgets = {
            'type': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Description de la recommandation...'
            }),
            'efficiency_score': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 1,
                'step': 0.01
            }),
        }