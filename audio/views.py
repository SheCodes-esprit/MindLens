from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from .models import AudioEntry, AudioEmotionAnalysis
from .forms import AudioEntryForm
from users.models import User
import base64
from django.utils import timezone
from datetime import datetime, timedelta

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from .models import AudioEntry, AudioEmotionAnalysis
from .forms import AudioEntryForm
from users.models import User
import base64
from django.utils import timezone
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger(__name__)

def perform_ai_analysis(audio_entry):
    audio_entry.ai_transcript = "Mock transcription: Today I felt stressed about work."
    audio_entry.save()
    
    AudioEmotionAnalysis.objects.create(
        audio_entry=audio_entry,
        detected_emotion='stress',
        intensity=0.75,
        ai_model_version='mock_v1'
    )
    AudioEmotionAnalysis.objects.create(
        audio_entry=audio_entry,
        detected_emotion='joy',
        intensity=0.3,
        ai_model_version='mock_v1'
    )

@login_required
def audio_create(request):
    if request.user.role != User.JOURNALIST:
        return redirect('dashboard')
    
    # Define the daily limit
    DAILY_ENTRY_LIMIT = 150
    
    # Get the start and end of today
    today = timezone.now().date()
    start_of_day = timezone.make_aware(datetime.combine(today, datetime.min.time()))
    end_of_day = timezone.make_aware(datetime.combine(today, datetime.max.time()))
    
    # Log first access of the day (optional)
    last_access = request.session.get('last_entry_check_date')
    if last_access != str(today):
        logger.info(f"Daily audio entry limit reset for user {request.user.username} at {timezone.now()}")
        request.session['last_entry_check_date'] = str(today)
    
    # Count entries for today
    today_entries = AudioEntry.objects.filter(
        user=request.user,
        created_at__range=(start_of_day, end_of_day)
    ).count()
    
    # Calculate remaining entries
    remaining_entries = DAILY_ENTRY_LIMIT - today_entries
    
    # Check if limit is reached
    if today_entries >= DAILY_ENTRY_LIMIT:
        return render(request, 'frontoffice/pages/audio/audio_create.html', {
            'form': AudioEntryForm(),
            'error': 'You have reached the daily limit of 150 audio entries.',
            'remaining_entries': 0
        })
    
    if request.method == 'POST':
        form = AudioEntryForm(request.POST, request.FILES)
        if form.is_valid():
            audio_entry = form.save(commit=False)
            audio_entry.user = request.user
            audio_entry.created_at = timezone.now()
            
            # Handle recorded audio if present
            recorded_audio = form.cleaned_data.get('recorded_audio')
            if recorded_audio:
                format, audio_str = recorded_audio.split(';base64,')
                ext = format.split('/')[-1]
                audio_data = base64.b64decode(audio_str)
                file_name = f"recording_{audio_entry.user.username}_{audio_entry.created_at.strftime('%Y%m%d%H%M%S')}.{ext}"
                audio_entry.audio_url.save(file_name, ContentFile(audio_data))
            
            audio_entry.save()
            perform_ai_analysis(audio_entry)
            return redirect('audio_list')
    else:
        form = AudioEntryForm()
    
    return render(request, 'frontoffice/pages/audio/audio_create.html', {
        'form': form,
        'remaining_entries': remaining_entries
    })
@login_required
def audio_list(request):
    if request.user.role != User.JOURNALIST:
        return redirect('dashboard')
    entries = AudioEntry.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'frontoffice/pages/audio/audio_list.html', {'entries': entries})


@login_required
def audio_detail(request, pk):
    if request.user.role != User.JOURNALIST:
        return redirect('dashboard')
    entry = get_object_or_404(AudioEntry, pk=pk, user=request.user)
    analyses = entry.emotion_analyses.all()
    return render(request, 'frontoffice/pages/audio/audio_detail.html', {'entry': entry, 'analyses': analyses})

@login_required
def audio_delete(request, pk):
    if request.user.role != User.JOURNALIST:
        return redirect('dashboard')
    entry = get_object_or_404(AudioEntry, pk=pk, user=request.user)
    if request.method == 'POST':
        entry.delete()
        return redirect('audio_list')
    return redirect('audio_detail', pk=pk)