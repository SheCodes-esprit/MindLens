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
import whisper
import re
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Max
from collections import defaultdict
from django.utils.timezone import make_aware, localdate
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
import io
from collections import defaultdict
from django.utils.timezone import localdate
from django.db.models import Count, Sum, Q
import json
from django.db.models import Sum, Avg, Count, Max, Q
from django.utils.timezone import now
from django.db.models import Sum
from django.contrib.admin.views.decorators import staff_member_required
import logging
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Whisper model
whisper_model = whisper.load_model("base")

def perform_ai_analysis(audio_entry):
    """
    Performs transcription and emotion analysis for a given AudioEntry.
    1. Transcribes audio using Whisper.
    2. Performs emotion analysis using keyword-based detection.
    3. Saves detected emotions in AudioEmotionAnalysis.
    """
    if not audio_entry.audio_url:
        logger.info("No audio file found for analysis.")
        return

    # Step 1: Transcribe audio
    transcript = ""
    try:
        result = whisper_model.transcribe(audio_entry.audio_url.path, task="translate")
        transcript = result.get('text', '').strip()
        if not transcript:
            audio_entry.ai_transcript = "No speech detected."
            audio_entry.save()
            logger.info("Transcript is empty after transcription.")
            return
        audio_entry.ai_transcript = transcript
        audio_entry.save()
        logger.info(f"Transcript: {transcript}")
    except Exception as e:
        logger.error(f"Whisper transcription failed: {e}")
        audio_entry.ai_transcript = "Transcription failed."
        audio_entry.save()
        return

    # Step 2: Skip emotion analysis if transcript too short
    if len(transcript) < 3:
        logger.info("Transcript too short for emotion analysis")
        return

    # Step 3: Perform emotion analysis using keyword-based approach
    try:
        emotions = analyze_emotions_keyword_based(transcript)
        logger.info(f"Detected emotions: {emotions}")

        # Step 4: Save emotions in the database
        for emotion, intensity in emotions.items():
            if intensity >= 0.01:
                AudioEmotionAnalysis.objects.create(
                    audio_entry=audio_entry,
                    detected_emotion=emotion,
                    intensity=intensity,
                    ai_model_version='whisper_base + keyword_analysis'
                )
        if not any(v >= 0.01 for v in emotions.values()):
            logger.info("No significant emotions detected.")

    except Exception as e:
        logger.error(f"Emotion analysis failed: {e}")

def analyze_emotions_keyword_based(text):
    """
    Analyzes emotions in text using keyword matching.
    Returns a dictionary with emotion scores between 0 and 1.
    """
    text_lower = text.lower()
    
    emotion_keywords = {
        'Happy': [
            'happy', 'joy', 'joyful', 'excited', 'wonderful', 'great', 'amazing', 
            'love', 'fun', 'enjoyed', 'delighted', 'pleased', 'cheerful', 'glad',
            'fantastic', 'excellent', 'awesome', 'brilliant', 'perfect', 'beautiful',
            'laugh', 'laughing', 'smile', 'smiling', 'best', 'good', 'nice'
        ],
        'Sad': [
            'sad', 'unhappy', 'depressed', 'miserable', 'disappointed', 'down', 
            'upset', 'hurt', 'crying', 'tears', 'lonely', 'hopeless', 'gloomy',
            'sorry', 'regret', 'miss', 'lost', 'bad', 'terrible', 'awful'
        ],
        'Angry': [
            'angry', 'mad', 'furious', 'annoyed', 'irritated', 'frustrated', 
            'rage', 'hate', 'outraged', 'pissed', 'upset', 'disgusted'
        ],
        'Fear': [
            'afraid', 'scared', 'fear', 'worried', 'anxious', 'nervous', 
            'terrified', 'panic', 'frightened', 'stress', 'stressed', 'concern'
        ],
        'Surprise': [
            'surprised', 'shocked', 'amazed', 'astonished', 'unexpected', 
            'wow', 'incredible', 'unbelievable', 'omg', 'whoa'
        ]
    }
    
    # Count matches for each emotion
    emotion_scores = {}
    words = text_lower.split()
    total_words = len(words)
    
    for emotion, keywords in emotion_keywords.items():
        match_count = 0
        matched_words = set()
        
        for keyword in keywords:
            # Use word boundaries to match whole words
            pattern = r'\b' + re.escape(keyword) + r'\w*\b'
            matches = re.findall(pattern, text_lower)
            match_count += len(matches)
            matched_words.update(matches)
        
        if match_count > 0:
            # Base score from keyword density
            base_score = (match_count / max(total_words, 1)) * 10
            
            # Bonus for multiple different emotional words
            variety_bonus = len(matched_words) * 0.15
            
            # Final intensity (capped at 1.0 for database storage)
            intensity = min(base_score + variety_bonus, 1.0)
        else:
            intensity = 0.0
        
        emotion_scores[emotion] = round(intensity, 4)
    
    return emotion_scores

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
    
    search_title = request.GET.get('search_title', '').strip()
    search_mood = request.GET.get('search_mood', '').strip()
    
    # Start with all entries for the user
    entries = AudioEntry.objects.filter(user=request.user).order_by('-created_at')
    
    if search_title:
        entries = entries.filter(title__icontains=search_title)
    
    if search_mood:
        entries = entries.filter(emotion_analyses__detected_emotion=search_mood).distinct()
    
    all_emotions = AudioEmotionAnalysis.objects.filter(
        audio_entry__user=request.user
    ).values_list('detected_emotion', flat=True).distinct().order_by('detected_emotion')

    # Group entries by month and paginate
    entries_by_month = defaultdict(list)
    for entry in entries:
        month_key = entry.created_at.date().replace(day=1)
        entries_by_month[month_key].append(entry)

    # Sort months in descending order
    sorted_months = sorted(entries_by_month.keys(), reverse=True)
    
    # Paginate entries for each month
    paginated_entries_by_month = {}
    for month in sorted_months:
        month_entries = entries_by_month[month]
        paginator = Paginator(month_entries, 3)  # 3 entries per page
        page_number = request.GET.get(f'page_{month.strftime("%Y_%m")}', 1)
        try:
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
        paginated_entries_by_month[month] = {
            'entries': page_obj,
            'paginator': paginator,
            'page_number': page_number
        }

    today = timezone.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_week = timezone.make_aware(datetime.combine(start_of_week, datetime.min.time()))
    end_of_week = start_of_week + timedelta(days=6, hours=23, minutes=59, seconds=59)
    
    start_of_month = today.replace(day=1)
    start_of_month = timezone.make_aware(datetime.combine(start_of_month, datetime.min.time()))
    end_of_month = (start_of_month + timedelta(days=31)).replace(day=1) - timedelta(seconds=1)

    weekly_entries = AudioEntry.objects.filter(
        user=request.user,
        created_at__range=(start_of_week, end_of_week)
    ).count()
    
    monthly_entries = AudioEntry.objects.filter(
        user=request.user,
        created_at__range=(start_of_month, end_of_month)
    ).count()
    
    total_entries = AudioEntry.objects.filter(user=request.user).count()
    
    total_duration = AudioEntry.objects.filter(
        user=request.user
    ).aggregate(total=Sum('duration'))['total'] or 0
    total_hours = int(total_duration // 3600)
    total_minutes = int((total_duration % 3600) // 60)
    
    streak = calculate_entry_streak(request.user)
    
    oldest_entry = AudioEntry.objects.filter(user=request.user).order_by('created_at').first()
    if oldest_entry:
        days_since_first = (today - oldest_entry.created_at.date()).days + 1
        weeks_active = max(days_since_first / 7, 1)
        avg_per_week = round(total_entries / weeks_active, 1)
    else:
        avg_per_week = 0
    
    emotion_counts = AudioEmotionAnalysis.objects.filter(
        audio_entry__user=request.user
    ).values('detected_emotion').annotate(count=Count('detected_emotion')).order_by('-count')
    
    most_frequent_emotion = emotion_counts.first()['detected_emotion'] if emotion_counts.exists() else 'None'
    
    emotion_labels = [item['detected_emotion'] for item in emotion_counts]
    emotion_data = [item['count'] for item in emotion_counts]
    emotion_chart_data = json.dumps({
        'labels': emotion_labels,
        'data': emotion_data
    })
    
    weekly_activity = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_start = timezone.make_aware(datetime.combine(day, datetime.min.time()))
        day_end = timezone.make_aware(datetime.combine(day, datetime.max.time()))
        count = AudioEntry.objects.filter(
            user=request.user,
            created_at__range=(day_start, day_end)
        ).count()
        weekly_activity.append({
            'day': day.strftime('%a'),
            'date': day.strftime('%m/%d'),
            'count': count
        })
    
    weekly_activity_json = json.dumps(weekly_activity)

    return render(request, 'frontoffice/pages/audio/audio_list.html', {
        'entries_by_month': paginated_entries_by_month,
        'weekly_entries': weekly_entries,
        'monthly_entries': monthly_entries,
        'total_entries': total_entries,
        'total_hours': total_hours,
        'total_minutes': total_minutes,
        'entry_streak': streak,
        'avg_per_week': avg_per_week,
        'most_frequent_emotion': most_frequent_emotion,
        'emotion_chart_data': emotion_chart_data,
        'weekly_activity_json': weekly_activity_json,
        'search_title': search_title,
        'search_mood': search_mood,
        'all_emotions': all_emotions,
    })

def calculate_entry_streak(user):
    """Calculate the current entry streak (consecutive days with entries)"""
    today = timezone.now().date()
    streak = 0
    current_date = today
    
    while True:
        day_start = timezone.make_aware(datetime.combine(current_date, datetime.min.time()))
        day_end = timezone.make_aware(datetime.combine(current_date, datetime.max.time()))
        
        has_entry = AudioEntry.objects.filter(
            user=user,
            created_at__range=(day_start, day_end)
        ).exists()
        
        if has_entry:
            streak += 1
            current_date -= timedelta(days=1)
        else:
            break
    
    return streak



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



# ──────────────────────────────────────────────────────────────────────
#  ADMIN AUDIO HISTORY – with stats, search, mood filter & sidebar count
# ──────────────────────────────────────────────────────────────────────


@login_required
def admin_audio_history_pdf(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="audio_history.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=60, bottomMargin=30)
    styles = getSampleStyleSheet()
    elements = []

    # Custom styles
    title_style = ParagraphStyle(
        'title_style',
        parent=styles['Title'],
        fontSize=18,
        textColor=colors.HexColor('#004c6d'),
        alignment=1,  # center
        spaceAfter=12
    )
    subtitle_style = ParagraphStyle(
        'subtitle_style',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#555555'),
        alignment=1,
        spaceAfter=12
    )

    # Title
    elements.append(Paragraph("Audio History Report", title_style))
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", subtitle_style))
    elements.append(Spacer(1, 12))

    # Fetch audio entries
    audios = AudioEntry.objects.select_related('user').order_by('-created_at')

    # Summary
    total_entries = audios.count()
    total_duration_sec = sum(a.duration or 0 for a in audios)
    total_hours = int(total_duration_sec // 3600)
    total_minutes = int((total_duration_sec % 3600) // 60)
    summary_text = f"<b>Total Entries:</b> {total_entries} &nbsp;&nbsp;&nbsp; <b>Total Duration:</b> {total_hours}h {total_minutes}m"
    elements.append(Paragraph(summary_text, styles['Normal']))
    elements.append(Spacer(1, 12))

    # Table header
    data = [["Title", "Journalist", "Duration (s)", "Created", "Dominant Emotion"]]

    # Table rows
    for audio in audios:
        data.append([
            audio.title or "Untitled",
            audio.user.username,
            f"{audio.duration:.1f}" if audio.duration else "–",
            audio.created_at.strftime("%d %b %Y %H:%M"),
            getattr(audio, "dominant_emotion", "–"),
        ])

    # Table styling
    table = Table(data, colWidths=[6*cm, 3*cm, 2.5*cm, 3.5*cm, 3.5*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#004c6d')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
    ]))

    # Alternating row colors
    for i in range(1, len(data)):
        bg_color = colors.HexColor('#f5f5f5') if i % 2 == 0 else colors.white
        table.setStyle([('BACKGROUND', (0, i), (-1, i), bg_color)])

    elements.append(table)

    # Header & Footer
    def header_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 9)
        # Header
        canvas.drawString(30, 820, "MindLens - Admin Report")
        canvas.drawRightString(570, 820, "Audio Archive")
        # Footer
        canvas.drawString(30, 15, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        canvas.drawRightString(570, 15, f"Page {doc.page}")
        canvas.restoreState()

    # Build PDF
    doc.build(elements, onFirstPage=header_footer, onLaterPages=header_footer)

    return response



logger = logging.getLogger(__name__)
@staff_member_required
def admin_audio_history(request):
    # Fetch all audio entries
    entries = AudioEntry.objects.select_related('user').order_by('-created_at')

    # Filters
    search = request.GET.get('search', '').strip()
    mood = request.GET.get('mood', '').strip()

    if search:
        entries = entries.filter(
            Q(title__icontains=search) |
            Q(user__username__icontains=search)
        )

    if mood:
        entries = entries.filter(emotion_analyses__detected_emotion__iexact=mood)

    entries = entries.distinct()

    # Pagination
    paginator = Paginator(entries, 5)  # 5 entries per page
    page_number = request.GET.get('page')
    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.get_page(1)
    except EmptyPage:
        page_obj = paginator.get_page(paginator.num_pages)

    # Basic Stats
    total = entries.count()
    total_duration = entries.aggregate(total=Sum('duration'))['total'] or 0
    total_hours = total_duration // 3600
    total_minutes = (total_duration % 3600) // 60
    avg_duration = round(total_duration / total, 1) if total else 0
    entries_today = entries.filter(created_at__date=localdate()).count()

    # Emotion Stats
    emotion_stats = AudioEmotionAnalysis.objects.filter(audio_entry__in=entries).values('detected_emotion').annotate(
        total_count=Count('detected_emotion'),
        avg_intensity=Avg('intensity')
    ).order_by('-total_count')

    emotion_chart_data = {
        'labels': [e['detected_emotion'] for e in emotion_stats] if emotion_stats else [],
        'counts': [e['total_count'] for e in emotion_stats] if emotion_stats else [],
        'avg_intensities': [round(e['avg_intensity'], 2) for e in emotion_stats] if emotion_stats else []
    }
    emotion_chart_data_json = json.dumps(emotion_chart_data)
    logger.info(f"Emotion chart data: {emotion_chart_data_json}")

    # Weekly Trend
    today = localdate()
    weekly_trend = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_start = make_aware(datetime.combine(day, datetime.min.time()))
        day_end = make_aware(datetime.combine(day, datetime.max.time()))
        day_count = entries.filter(created_at__range=(day_start, day_end)).count()
        weekly_trend.append({
            'day': day.strftime('%a'),
            'date': day.strftime('%m/%d'),
            'count': day_count
        })
    weekly_trend_json = json.dumps(weekly_trend)
    logger.info(f"Weekly trend data: {weekly_trend_json}")

    # Monthly Trend
    monthly_trend = entries.filter(created_at__year=today.year).values('created_at__month').annotate(
        monthly_count=Count('id')
    ).order_by('created_at__month')
    monthly_trend_data = {
        'labels': [datetime(today.year, m['created_at__month'], 1).strftime('%b') for m in monthly_trend] if monthly_trend else [],
        'counts': [m['monthly_count'] for m in monthly_trend] if monthly_trend else []
    }
    monthly_trend_json = json.dumps(monthly_trend_data)
    logger.info(f"Monthly trend data: {monthly_trend_json}")

    # Per-user stats
    user_stats = entries.values('user__username').annotate(
        user_entries=Count('id'),
        user_duration=Sum('duration')
    ).order_by('-user_entries')
    top_users = user_stats[:5]

    # Most frequent mood
    mood_counts = AudioEmotionAnalysis.objects.filter(audio_entry__in=entries).values('detected_emotion').annotate(
        count=Count('detected_emotion')
    ).order_by('-count')
    most_frequent_mood = mood_counts[0]['detected_emotion'] if mood_counts else 'None'

    all_moods = AudioEmotionAnalysis.objects.values_list('detected_emotion', flat=True).distinct().order_by('detected_emotion')

    context = {
        'page_obj': page_obj,  # Paginated entries
        'total': total,
        'total_hours': total_hours,
        'total_minutes': total_minutes,
        'avg_duration': avg_duration,
        'entries_today': entries_today,
        'most_frequent_mood': most_frequent_mood,
        'all_moods': all_moods,
        'search': search,
        'mood': mood,
        'emotion_chart_data_json': emotion_chart_data_json,
        'weekly_trend_json': weekly_trend_json,
        'monthly_trend_json': monthly_trend_json,
        'top_users': top_users,
    }

    return render(request, 'backoffice/pages/audio_history.html', context)