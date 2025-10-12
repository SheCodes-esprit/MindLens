from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import AudioEntry, AudioEmotionAnalysis
from .forms import AudioEntryForm
from users.models import User  # Ensure User is imported if needed

# Placeholder for AI integration (e.g., transcription and emotion analysis)
def perform_ai_analysis(audio_entry):
    # TODO: Integrate with external APIs like OpenAI Whisper, AssemblyAI, etc.
    # For now, mock some data
    # Example: Transcribe audio (placeholder)
    audio_entry.ai_transcript = "Mock transcription: Today I felt stressed about work."
    audio_entry.save()
    
    # Mock emotion analysis
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
def audio_list(request):
    if request.user.role != User.JOURNALIST:
        return redirect('dashboard')  # Redirect admins or others
    entries = AudioEntry.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'frontoffice/pages/audio/audio_list.html', {'entries': entries})

@login_required
def audio_create(request):
    if request.user.role != User.JOURNALIST:
        return redirect('dashboard')
    if request.method == 'POST':
        form = AudioEntryForm(request.POST, request.FILES)
        if form.is_valid():
            audio_entry = form.save(commit=False)
            audio_entry.user = request.user
            audio_entry.save()
            # Perform AI analysis (transcription, emotion detection, summary)
            perform_ai_analysis(audio_entry)
            return redirect('audio_list')
    else:
        form = AudioEntryForm()
    return render(request, 'frontoffice/pages/audio/audio_create.html', {'form': form})

@login_required
def audio_detail(request, pk):
    if request.user.role != User.JOURNALIST:
        return redirect('dashboard')
    entry = get_object_or_404(AudioEntry, pk=pk, user=request.user)
    analyses = entry.emotion_analyses.all()
    # TODO: Generate graph for emotion evolution (use Chart.js or similar in template)
    return render(request, 'frontoffice/pages/audio/audio_detail.html', {'entry': entry, 'analyses': analyses})