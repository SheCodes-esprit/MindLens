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
from django.db.models import Count
from pydub import AudioSegment
import os
import whisper
from pydub import AudioSegment
from pydub.utils import which

AudioSegment.converter = r"C:\Users\chaym\Downloads\ffmpeg-8.0-essentials_build\ffmpeg-8.0-essentials_build\bin\ffmpeg.exe"
AudioSegment.ffprobe = r"C:\Users\chaym\Downloads\ffmpeg-8.0-essentials_build\ffmpeg-8.0-essentials_build\bin\ffprobe.exe"
# You can choose model sizes: tiny, base, small, medium, large
whisper_model = whisper.load_model("base")
# Configure logging
logger = logging.getLogger(__name__)

def perform_ai_analysis(audio_entry):
    if audio_entry.audio_url:
        try:
            # Transcribe the uploaded audio file
            result = whisper_model.transcribe(audio_entry.audio_url.path)
            audio_entry.ai_transcript = result['text']
            audio_entry.save()

            # Optionally, you can keep your emotion mock for now
            AudioEmotionAnalysis.objects.create(
                audio_entry=audio_entry,
                detected_emotion='stress',
                intensity=0.75,
                ai_model_version='whisper_base'
            )
            AudioEmotionAnalysis.objects.create(
                audio_entry=audio_entry,
                detected_emotion='joy',
                intensity=0.3,
                ai_model_version='whisper_base'
            )
        except Exception as e:
            # Logging in case transcription fails
            logger.error(f"Whisper transcription failed: {e}")
            audio_entry.ai_transcript = "Transcription failed."
            audio_entry.save()

@login_required
def audio_create(request):
    if request.user.role != User.JOURNALIST:
        return redirect('dashboard')
    
    DAILY_ENTRY_LIMIT = 15
    today = timezone.now().date()
    start_of_day = timezone.make_aware(datetime.combine(today, datetime.min.time()))
    end_of_day = timezone.make_aware(datetime.combine(today, datetime.max.time()))
    
    last_access = request.session.get('last_entry_check_date')
    if last_access != str(today):
        logger.info(f"Daily audio entry limit reset for user {request.user.username} at {timezone.now()}")
        request.session['last_entry_check_date'] = str(today)
    
    today_entries = AudioEntry.objects.filter(
        user=request.user,
        created_at__range=(start_of_day, end_of_day)
    ).count()
    
    remaining_entries = DAILY_ENTRY_LIMIT - today_entries
    
    if today_entries >= DAILY_ENTRY_LIMIT:
        return render(request, 'frontoffice/pages/audio/audio_create.html', {
            'form': AudioEntryForm(),
            'error': 'You have reached the daily limit of 15 audio entries.',
            'remaining_entries': 0
        })
    
    if request.method == 'POST':
        form = AudioEntryForm(request.POST, request.FILES)
        if form.is_valid():
            audio_entry = form.save(commit=False)
            audio_entry.user = request.user
            audio_entry.created_at = timezone.now()
            
            # Handle recorded audio
            recorded_audio = form.cleaned_data.get('recorded_audio')
            if recorded_audio:
                format, audio_str = recorded_audio.split(';base64,')
                ext = format.split('/')[-1]
                audio_data = base64.b64decode(audio_str)
                file_name = f"recording_{audio_entry.user.username}_{audio_entry.created_at.strftime('%Y%m%d%H%M%S')}.{ext}"
                audio_entry.audio_url.save(file_name, ContentFile(audio_data))
                
                audio_entry.save()
                try:
                    audio = AudioSegment.from_file(audio_entry.audio_url.path)
                    audio_entry.duration = len(audio) / 1000.0
                    logger.info(f"Recorded audio duration: {audio_entry.duration} seconds")
                except Exception as e:
                    logger.error(f"Error calculating duration for recorded audio: {e}")
                    audio_entry.duration = 0.0
                audio_entry.save(update_fields=['duration'])
            
            # Handle uploaded audio
            elif form.cleaned_data.get('audio_url'):
                audio_file = form.cleaned_data['audio_url']
                audio_entry.audio_url = audio_file
                audio_entry.save()
                
                try:
                    audio = AudioSegment.from_file(audio_entry.audio_url.path)
                    audio_entry.duration = len(audio) / 1000.0
                    logger.info(f"Uploaded audio duration: {audio_entry.duration} seconds")
                except Exception as e:
                    logger.error(f"Error calculating duration for uploaded audio: {e}")
                    audio_entry.duration = 0.0
                audio_entry.save(update_fields=['duration'])
            
            if not audio_entry.pk:
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
    
    today = timezone.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_week = timezone.make_aware(datetime.combine(start_of_week, datetime.min.time()))
    end_of_week = start_of_week + timedelta(days=6, hours=23, minutes=59, seconds=59)
    
    start_of_month = today.replace(day=1)
    start_of_month = timezone.make_aware(datetime.combine(start_of_month, datetime.min.time()))
    end_of_month = start_of_month + timedelta(days=31)
    end_of_month = end_of_month.replace(day=1) - timedelta(seconds=1)
    
    weekly_entries = AudioEntry.objects.filter(
        user=request.user,
        created_at__range=(start_of_week, end_of_week)
    ).count()
    
    monthly_entries = AudioEntry.objects.filter(
        user=request.user,
        created_at__range=(start_of_month, end_of_month)
    ).count()
    
    emotion_counts = AudioEmotionAnalysis.objects.filter(
        audio_entry__user=request.user
    ).values('detected_emotion').annotate(count=Count('detected_emotion')).order_by('-count')
    most_frequent_emotion = emotion_counts.first()['detected_emotion'] if emotion_counts.exists() else 'None'
    
    return render(request, 'frontoffice/pages/audio/audio_list.html', {
        'entries': entries,
        'weekly_entries': weekly_entries,
        'monthly_entries': monthly_entries,
        'most_frequent_emotion': most_frequent_emotion,
    })

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
