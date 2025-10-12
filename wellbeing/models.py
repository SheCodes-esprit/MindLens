from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()

class WellbeingRecord(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wellbeing_records')
    date = models.DateField(auto_now_add=True)
    mood_score = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Mood score from 1-10"
    )
    energy_level = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Energy level from 1-10"
    )
    sleep_hours = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(24)],
        help_text="Hours of sleep"
    )
    productivity_score = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Productivity score from 1-10"
    )
    ai_summary = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-date']
        verbose_name = 'Wellbeing Record'
        verbose_name_plural = 'Wellbeing Records'
    
    def __str__(self):
        return f"{self.user.username} - {self.date}"


class RoutineRecommendation(models.Model):
    ROUTINE_TYPES = [
        ('morning', 'Morning Routine'),
        ('evening', 'Evening Routine'),
        ('exercise', 'Exercise'),
        ('meditation', 'Meditation'),
        ('nutrition', 'Nutrition'),
        ('sleep', 'Sleep Hygiene'),
        ('productivity', 'Productivity Tip'),
        ('stress', 'Stress Management'),
    ]
    
    id = models.AutoField(primary_key=True)
    wellbeing_record = models.ForeignKey(
        WellbeingRecord, 
        on_delete=models.CASCADE, 
        related_name='recommendations'
    )
    type = models.CharField(max_length=50, choices=ROUTINE_TYPES)
    description = models.TextField()
    ai_generated = models.BooleanField(default=True)
    efficiency_score = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text="Efficiency score from 0-1"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Routine Recommendation'
        verbose_name_plural = 'Routine Recommendations'
    
    def __str__(self):
        return f"{self.type} - {self.wellbeing_record.user.username}"