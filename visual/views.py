from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import VisualEntryForm
from .models import VisualEntry, VisualInsight
from transformers import DetrImageProcessor, DetrForObjectDetection
from PIL import Image
import torch
import cv2
from colorthief import ColorThief
from django.conf import settings
import requests, os
from fer import FER
import numpy as np
from moviepy.editor import VideoFileClip
from io import BytesIO
import json
import os
from dotenv import load_dotenv
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db.models import Count, Avg
from django.db.models.functions import TruncDay, TruncWeek
from django.views.decorators.cache import cache_page
from datetime import datetime, date, timedelta
from collections import Counter
from .forms import VisualEntryForm
from .models import VisualEntry, VisualInsight
from transformers import DetrImageProcessor, DetrForObjectDetection
from PIL import Image
import torch
import cv2
from colorthief import ColorThief
from django.conf import settings
from fer import FER
import numpy as np
from moviepy.editor import VideoFileClip
from io import BytesIO
import json
import requests
import random
from django.views.decorators.http import require_GET, require_POST
# ----------------------  STATISTIQUES ----------------------

from django.db.models import Count, Avg
from django.db.models.functions import TruncDay
from django.http import JsonResponse
from django.views.decorators.cache import cache_page
from datetime import date, timedelta
from django.db.models.functions import TruncWeek

# ---------------------- LIST & DETAIL ----------------------
from django.utils import timezone
from collections import Counter

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import VisualEntryForm
from .models import VisualEntry, VisualInsight
from django.utils import timezone
from datetime import timedelta
import json


# 1️⃣ Filtrage intelligent
@login_required
def api_visuals_filtered(request):
    start = request.GET.get('start_date')
    end = request.GET.get('end_date')
    emotion = request.GET.get('emotion')

    qs = VisualEntry.objects.filter(user=request.user)
    if start:
        qs = qs.filter(created_at__date__gte=start)
    if end:
        qs = qs.filter(created_at__date__lte=end)
    if emotion:
        qs = qs.filter(insights__emotion_detected=emotion).distinct()

    data = []
    for entry in qs:
        latest = entry.insights.order_by('-created_at').first()
        data.append({
            "id": entry.id,
            "type": entry.type,
            "media_url": entry.media_url.url,
            "emotion": latest.emotion_detected if latest else "",
            "created_at": entry.created_at.strftime("%Y-%m-%d")
        })
    return JsonResponse({"results": data})


# 2️⃣ Timeline émotionnelle
@login_required
def api_visuals_timeline(request):
    items = []
    qs = VisualInsight.objects.filter(visual_entry__user=request.user).order_by('created_at')
    for ins in qs:
        items.append({
            "id": ins.id,
            "start": ins.created_at.isoformat(),
            "content": ins.emotion_detected or "N/A",
            "media": ins.visual_entry.media_url.url
        })
    return JsonResponse(items, safe=False)


# 3️⃣ Albums thématiques automatiques
@login_required
def api_generate_albums(request):
    categories = {
        "Nature": ["tree", "mountain", "sky", "ocean"],
        "People": ["person", "face", "smile"],
        "Food": ["food", "dish", "plate"],
    }
    insights = VisualInsight.objects.filter(visual_entry__user=request.user)
    albums = {name: [] for name in categories}
    for ins in insights:
        for cat, tags in categories.items():
            if any(tag in ins.tags_generated for tag in tags):
                albums[cat].append(ins.visual_entry.media_url.url)
    return JsonResponse({"albums": albums})



@login_required
def visual_list(request):
    # Filtrage des entrées
    search_title = request.GET.get('search_title', '')
    search_mood = request.GET.get('search_mood', '')
    
    entries = VisualEntry.objects.filter(user=request.user).order_by('-created_at')
    if search_title:
        entries = entries.filter(title__icontains=search_title)
    if search_mood:
        entries = entries.filter(insights__emotion_detected=search_mood).distinct()

    # Statistiques
    total_entries = entries.count()
    one_week_ago = timezone.now() - timedelta(days=7)
    one_month_ago = timezone.now() - timedelta(days=30)
    weekly_entries = entries.filter(created_at__gte=one_week_ago).count()
    monthly_entries = entries.filter(created_at__gte=one_month_ago).count()

    # Streak (jours consécutifs avec des posts)
    dates = entries.values_list('created_at__date', flat=True).distinct()
    dates = sorted(set(dates), reverse=True)
    streak = 0
    current_date = date.today()
    for d in dates:
        if d == current_date:
            streak += 1
            current_date -= timedelta(days=1)
        else:
            break
    entry_streak = streak

    # Temps total (supposition : pas de durée pour les visuels, donc 0)
    total_hours = 0
    total_minutes = 0

    # Moyenne par semaine
    weeks = 8
    start_date = date.today() - timedelta(weeks=weeks-1)
    avg_per_week = entries.filter(created_at__date__gte=start_date).count() / weeks

    # Émotion la plus fréquente
    emotions = VisualInsight.objects.filter(visual_entry__user=request.user).values('emotion_detected').annotate(count=Count('id')).order_by('-count')
    most_frequent_emotion = emotions[0]['emotion_detected'] if emotions else 'N/A'

    # Toutes les émotions pour le filtre
    all_emotions = VisualInsight.objects.filter(visual_entry__user=request.user).values_list('emotion_detected', flat=True).distinct()

    # Données pour le graphique d'activité hebdomadaire
    last_entry = entries.order_by('-created_at').first()
    weekly_activity = []
    if last_entry:
        week_start = last_entry.created_at.date() - timedelta(days=last_entry.created_at.weekday())
        week_days = [week_start + timedelta(days=i) for i in range(7)]
        qs = (
            entries
            .filter(created_at__date__gte=week_start, created_at__date__lte=week_start + timedelta(days=6))
            .annotate(day=TruncDay('created_at'))
            .values('day')
            .annotate(count=Count('id'))
        )
        counts_dict = {r['day'].date(): r['count'] for r in qs}
        weekly_activity = [{'day': d.strftime('%a'), 'count': counts_dict.get(d, 0)} for d in week_days]

    # Données pour le graphique de répartition des émotions
    emotion_data = [
        {'emotion': r['emotion_detected'] or 'unknown', 'count': r['count']}
        for r in VisualInsight.objects.filter(visual_entry__user=request.user)
        .values('emotion_detected')
        .annotate(count=Count('id'))
        .order_by('-count')
    ]
    emotion_chart_data = {
        'labels': [r['emotion'] for r in emotion_data],
        'data': [r['count'] for r in emotion_data]
    }

    context = {
        'entries': entries,
        'total_entries': total_entries,
        'weekly_entries': weekly_entries,
        'monthly_entries': monthly_entries,
        'entry_streak': entry_streak,
        'total_hours': total_hours,
        'total_minutes': total_minutes,
        'avg_per_week': round(avg_per_week, 1),
        'most_frequent_emotion': most_frequent_emotion,
        'all_emotions': all_emotions,
        'weekly_activity_json': json.dumps(weekly_activity),
        'emotion_chart_data': json.dumps(emotion_chart_data),
        'search_title': search_title,
        'search_mood': search_mood,
    }
    return render(request, 'frontoffice/pages/visual/visual_list.html', context)

@login_required
def visual_detail(request, pk):
    entry = get_object_or_404(VisualEntry, pk=pk, user=request.user)
    insights = entry.insights.all()
    return render(request, 'frontoffice/pages/visual/visual_detail.html', {'entry': entry, 'insights': insights})


# ---------------------- CREATE ----------------------

@login_required
def visual_detail(request, pk):
    entry = get_object_or_404(VisualEntry, pk=pk, user=request.user)
    insights = entry.insights.all()
    return render(request, 'frontoffice/pages/visual/visual_detail.html', {'entry': entry, 'insights': insights})


# ---------------------- CREATE ----------------------

@login_required
def visual_create(request):
    if request.method == 'POST':
        form = VisualEntryForm(request.POST, request.FILES)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.user = request.user
            entry.save()
            analyze_visual(entry)
            return redirect('visual_list')
    else:
        form = VisualEntryForm()
    return render(request, 'frontoffice/pages/visual/visual_create.html', {'form': form})


# ---------------------- DELETE ----------------------

@login_required
def visual_delete(request, pk):
    entry = get_object_or_404(VisualEntry, pk=pk, user=request.user)
    if request.method == 'POST':
        entry.delete()
        return redirect('visual_list')
    return render(request, 'frontoffice/pages/visual/visual_confirm_delete.html', {'entry': entry})


# ---------------------- ANALYSE PRINCIPALE ----------------------

def analyze_visual(entry):
    # 1️⃣ Device GPU/CPU
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # 2️⃣ Charger modèle DETR
    processor = DetrImageProcessor.from_pretrained("facebook/detr-resnet-50")
    model = DetrForObjectDetection.from_pretrained("facebook/detr-resnet-50").to(device)
    model.eval()

    # 3️⃣ Récupérer chemin fichier
    file_path = os.path.join(settings.MEDIA_ROOT, entry.media_url.name)
    file_ext = os.path.splitext(file_path)[1].lower()

    image_pil = None  # pour stocker l'image finale à analyser

    # 4️⃣ Gestion image / vidéo
    try:
        if file_ext in ['.jpg', '.jpeg', '.png', '.gif']:
            # --- Cas image ---
            image_pil = Image.open(file_path).convert("RGB")

        elif file_ext in ['.mp4', '.mov', '.avi', '.mkv']:
            # --- Cas vidéo : extraire une frame ---
            clip = VideoFileClip(file_path)
            frame = clip.get_frame(1)  # frame à 1s
            image_pil = Image.fromarray(frame)
            clip.close()

        else:
            entry.ai_description = "Unsupported file type for analysis."
            entry.save()
            return

        # Convertir pour FER (OpenCV utilise BGR)
        image_cv = cv2.cvtColor(np.array(image_pil), cv2.COLOR_RGB2BGR)

        # 5️⃣ Détection objets DETR
        inputs = processor(images=image_pil, return_tensors="pt")
        inputs = {k: v.to(device) for k, v in inputs.items()}
        with torch.no_grad():
            outputs = model(**inputs)

        target_sizes = torch.tensor([image_pil.size[::-1]], device=device)
        results = processor.post_process_object_detection(outputs, threshold=0.5, target_sizes=target_sizes)[0]
        detected_objects = [model.config.id2label[label.item()] for label in results["labels"]]

        # 6️⃣ Détection émotions FER
        detector = FER(mtcnn=True)
        emotion_scores = detector.detect_emotions(image_cv)
        if emotion_scores:
            top_emotion = max(emotion_scores[0]["emotions"], key=emotion_scores[0]["emotions"].get)
        else:
            top_emotion = "neutral"

        # 7️⃣ Couleurs dominantes (pour vidéos : sur frame extraite)
        buffer = BytesIO()
        image_pil.save(buffer, format="PNG")
        buffer.seek(0)
        color_thief = ColorThief(buffer)
        dominant_colors = color_thief.get_palette(color_count=3)

        # 8️⃣ Génération tags et score confiance
        tags_generated = detected_objects[:5]
        ai_confidence = (
            sum(results["scores"].tolist()) / len(results["scores"])
            if len(results["scores"]) > 0 else 0.0
        )

        # 9️⃣ Sauvegarde en base
        entry.ai_description = f"Détecté: {', '.join(detected_objects)}. Émotion: {top_emotion}."
        entry.save()

        VisualInsight.objects.create(
            visual_entry=entry,
            detected_objects=detected_objects,
            dominant_colors=dominant_colors,
            emotion_detected=top_emotion,
            tags_generated=tags_generated,
            ai_confidence=ai_confidence
        )

    except Exception as e:
        entry.ai_description = f"Erreur pendant l'analyse : {e}"
        entry.save()


@login_required
def stats_page(request):
    return render(request, 'frontoffice/pages/visual/visual_stats.html', {})


# ---------------------- API: trend posts ----------------------
@login_required
@cache_page(60*5)  # cache 5 minutes
def api_posts_trend(request):
    user = request.user
    days = int(request.GET.get('days', 30))
    start_date = date.today() - timedelta(days=days-1)

    qs = (
        VisualEntry.objects
        .filter(user=user, created_at__date__gte=start_date)
        .annotate(day=TruncDay('created_at'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )

    series = {r['day'].date().isoformat(): r['count'] for r in qs}
    out = []
    for i in range(days):
        d = start_date + timedelta(days=i)
        out.append({'date': d.isoformat(), 'count': series.get(d.isoformat(), 0)})

    return JsonResponse({'series': out})


# ---------------------- API: distribution émotions ----------------------

@login_required
@cache_page(60*5)
def api_posts_trend_weekly(request):
    user = request.user
    weeks = int(request.GET.get('weeks', 8))
    today = date.today()
    start_date = today - timedelta(weeks=weeks-1)

    qs = (
        VisualEntry.objects
        .filter(user=user, created_at__date__gte=start_date)
        .annotate(week=TruncWeek('created_at'))
        .values('week')
        .annotate(count=Count('id'))
        .order_by('week')
    )

    series = {r['week'].date().isoformat(): r['count'] for r in qs}

    out = []
    for i in range(weeks):
        d = start_date + timedelta(weeks=i)
        week_start = d - timedelta(days=d.weekday())
        out.append({
            'week_start': week_start.isoformat(),
            'count': series.get(week_start.isoformat(), 0)
        })

    return JsonResponse({'series': out})


@login_required
@cache_page(60*5)
def api_emotions_distribution(request):
    user = request.user
    qs = (
        VisualInsight.objects
        .filter(visual_entry__user=user)
        .values('emotion_detected')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    data = [{'emotion': r['emotion_detected'] or 'unknown', 'count': r['count']} for r in qs]
    return JsonResponse({'data': data})


@login_required
@cache_page(60*5)
def api_top_objects(request):
    user = request.user
    qs = VisualInsight.objects.filter(visual_entry__user=user).values('detected_objects')
    counter = {}
    for rec in qs:
        objs = rec['detected_objects'] or []
        for o in objs:
            name = str(o).strip().lower()
            if not name: continue
            counter[name] = counter.get(name, 0) + 1
    top = sorted(counter.items(), key=lambda x: x[1], reverse=True)[:20]
    data = [{'object': k, 'count': v} for k, v in top]
    return JsonResponse({'data': data})


@login_required
def api_posts_trend_week_days(request):
    """
    Retourne le nombre de posts pour chaque jour de la semaine contenant des posts,
    même si les autres jours sont à 0.
    """
    user = request.user
    # prendre la dernière semaine où il y a des posts
    last_entry = VisualEntry.objects.filter(user=user).order_by('-created_at').first()
    if not last_entry:
        return JsonResponse({'series': []})

    # lundi de cette semaine
    week_start = last_entry.created_at.date() - timedelta(days=last_entry.created_at.weekday())
    week_days = [week_start + timedelta(days=i) for i in range(7)]

    qs = (
        VisualEntry.objects
        .filter(user=user, created_at__date__gte=week_start, created_at__date__lte=week_start + timedelta(days=6))
        .annotate(day=TruncDay('created_at'))
        .values('day')
        .annotate(count=Count('id'))
    )

    counts_dict = {r['day'].date(): r['count'] for r in qs}

    series = [{'date': d.isoformat(), 'count': counts_dict.get(d, 0)} for d in week_days]
    return 


# mapping codes -> émotions lisibles (adapte selon ta BD)
EMOTION_MAP = {
    1: 'joyeux(se)',
    2: 'triste',
    3: 'en colère',
    4: 'surpris(e)',
    5: 'neutre',
    6: 'stressé(e)',
    7: 'fatigué(e)',
    79: 'calme'
}

# mapping émotion -> traits (exemple simple)
EMOTION_TRAIT_MAP = {
    'joyeux(se)': {'traits': ['optimiste', 'sociable'], 'weakness': ['peut éviter les problèmes'], 'advice': 'Continuez à partager votre joie, mais prenez aussi du recul si besoin.'},
    'triste': {'traits': ['réfléchi(e)', 'empathique'], 'weakness': ['isolement possible'], 'advice': "Parlez à quelqu'un et pratiquez une activité qui remonte le moral."},
    'en colère': {'traits': ['assertif(ve)'], 'weakness': ['impulsivité'], 'advice': 'Canalisez l’énergie par le sport ou l’écriture.'},
    'surpris(e)': {'traits': ['curieux(se)'], 'weakness': ['désorganisation'], 'advice': "Notez ce que vous ressentez pour mieux comprendre."},
    'neutre': {'traits': ['stable', 'réfléchi(e)'], 'weakness': ['manque de passion'], 'advice': "Cherchez une petite activité qui vous enthousiasme."},
    'stressé(e)': {'traits': ['dévoué(e)'], 'weakness': ['épuisement'], 'advice': "Planifiez des pauses et du sommeil réparateur."},
    'fatigué(e)': {'traits': ['résilient(e)'], 'weakness': ['baisse de concentration'], 'advice': "Priorisez le repos et hydratez-vous."},
    'calme': {'traits': ['posée', 'claire'], 'weakness': ['passivité'], 'advice': "Utilisez cette clarté pour fixer des objectifs concrets."}
}

@login_required
@require_GET

def personality_start(request):
    """
    GET: calcule émotion dominante à partir des 7 derniers jours et renvoie :
    - dominant_emotion (texte)
    - short_preanalysis (phrase courte)
    - questions: liste de {id, text}
    """
    # plage 7 jours
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    entries = VisualEntry.objects.filter(
        user=request.user,
        created_at__range=[start_date, end_date]
    ).values('insights').annotate(count=Count('insights')).order_by('-count')

    # si entries vide, valeur par défaut
    dominant_code = entries[0]['insights'] if entries else None
    dominant_emotion = EMOTION_MAP.get(dominant_code, 'neutre')

    # questions générées simplement à partir de l'émotion dominante
    # 5 questions Vrai/Faux — adapte le texte
    questions_bank = {
        'joyeux(se)': [
            "Je me sens généralement optimiste quant à l'avenir.",
            "Je cherche activement des occasions de socialiser.",
            "J'ai tendance à partager facilement mes réussites.",
            "Je remets rarement les tâches importantes à plus tard.",
            "Je prends du temps pour des activités qui m’amusent."
        ],
        'triste': [
            "Je me sens souvent incompris(e).",
            "J'ai tendance à garder mes émotions pour moi.",
            "Je suis parfois découragé(e) pour des petites choses.",
            "J'évite de parler de mes problèmes.",
            "Je me sens moins motivé(e) que d'habitude."
        ],
        # ... autres émotions ...
    }

    # fallback questions (neutre)
    fallback_questions = [
        "Je préfère planifier avant d’agir.",
        "Je me sens à l'aise pour demander de l'aide.",
        "Je termine généralement ce que je commence.",
        "Je me fixe des objectifs personnels réguliers.",
        "Je prends du temps pour moi chaque semaine."
    ]

    questions_texts = questions_bank.get(dominant_emotion, fallback_questions)
    # créer objects questions id
    questions = [{"id": i, "text": q} for i, q in enumerate(questions_texts, start=1)]

    preanalysis = f"On observe une tendance plutôt '{dominant_emotion}' ces derniers jours."

    return JsonResponse({
        "dominant_emotion": dominant_emotion,
        "preanalysis": preanalysis,
        "questions": questions
    })


@login_required
@require_POST
def personality_complete(request):
    """
    POST JSON: { answers: [{id:1, value:true}, ...], dominant_emotion: 'joyeux(se)' }
    Renvoie: profil (forces, faiblesses, recommandations, score)
    """
    try:
        data = json.loads(request.body)
        answers = data.get('answers', [])
        dominant_emotion = data.get('dominant_emotion', 'neutre')
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")

    # scoring simple: chaque "vrai" = 1 point
    total_questions = len(answers) or 1
    true_count = sum(1 for a in answers if a.get('value') is True)
    score_pct = int((true_count / total_questions) * 100)

    # récupérer traits depuis map
    trait_info = EMOTION_TRAIT_MAP.get(dominant_emotion, EMOTION_TRAIT_MAP['neutre'] if 'neutre' in EMOTION_TRAIT_MAP else {
        'traits': ['équilibré(e)'],
        'weakness': ['neutre'],
        'advice': "Restez attentif à vos besoins."
    })

    # Affiner l'analyse selon le score
    if score_pct >= 80:
        overall = "Profil très cohérent avec la tendance émotionnelle actuelle."
    elif score_pct >= 50:
        overall = "Profil partiellement cohérent — il y a des éléments à renforcer."
    else:
        overall = "Profil peu cohérent — il peut y avoir un décalage entre émotions et comportement."

    # construire rapport
    profile = {
        "dominant_emotion": dominant_emotion,
        "score_pct": score_pct,
        "overall": overall,
        "strengths": trait_info.get('traits', []),
        "weaknesses": trait_info.get('weakness', []),
        "advice": trait_info.get('advice', "")
    }

    # optionnel: sauvegarder en DB si tu crées un model PersonalitySession

    return JsonResponse({"profile": profile})


# Load environment variables
load_dotenv()

# ---------------------- Mood Story IA ----------------------
@login_required
def api_mood_story(request):
    days = int(request.GET.get('days', 7))
    tone = request.GET.get('tone', 'poetic')
    start_date = timezone.now() - timedelta(days=days)
    insights = VisualInsight.objects.filter(visual_entry__user=request.user, created_at__gte=start_date)
    emotions = [i.emotion_detected for i in insights if i.emotion_detected]
    if not emotions:
        return JsonResponse({"message": f"Pas assez de données pour les {days} derniers jours."})

    # Déterminer l'émotion dominante
    emotion_counts = Counter(emotions)
    dominant_emotion = emotion_counts.most_common(1)[0][0] if emotion_counts else 'neutral'

    # Préparer le prompt en fonction du ton
    tone_prompts = {
        'poetic': f"Raconte en 3 phrases poétiques cette période émotionnelle ({days} jours) : {', '.join(emotions)}",
        'humorous': f"Raconte de manière humoristique en 3 phrases cette période émotionnelle ({days} jours) : {', '.join(emotions)}",
        'analytic': f"Analyse en 3 phrases cette période émotionnelle ({days} jours) : {', '.join(emotions)}"
    }
    prompt = tone_prompts.get(tone, tone_prompts['poetic'])

    # Utiliser la clé API depuis .env
    api_key = os.getenv('HUGGINGFACE_API_KEY')
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {"inputs": prompt}
    response = requests.post(
        "https://api-inference.huggingface.co/models/facebook/bart-large-cnn",
        headers=headers,
        json=payload
    )
    if response.status_code != 200:
        return JsonResponse({"error": "Erreur API Hugging Face"}, status=500)

    data = response.json()
    story_text = data[0].get("summary_text", "Pas de réponse de l'IA.").split('. ')
    story_points = []
    for i, sentence in enumerate(story_text[:-1]):  # Exclure la dernière phrase vide
        insight = insights[i % len(insights)] if insights else None
        if insight and insight.visual_entry:
            media_url = insight.visual_entry.media_url.url
            media_type = "video" if media_url.lower().endswith('.mp4') else "image"
        else:
            media_url = ""
            media_type = "image"
        story_points.append({
            "date": insight.created_at.strftime("%d %b") if insight else timezone.now().strftime("%d %b"),
            "text": sentence + '.',
            "image": media_url
        })

    return JsonResponse({
        "intro": f"Bienvenue dans votre voyage émotionnel des {days} derniers jours !",
        "story_points": story_points,
        "conclusion": "Que cette histoire vous inspire pour demain.",
        "dominant_emotion": dominant_emotion,
        "mood_story": " ".join(story_text)
    })

# ---------------------- Mood Prediction ----------------------
@login_required
def mood_prediction(request):
    # Récupérer la clé API depuis .env
    api_key = os.getenv('HUGGINGFACE_API_KEY')
    if not api_key:
        return JsonResponse({"error": "Clé API Hugging Face non configurée"}, status=500)

    # Récupérer le paramètre 'period'
    period = request.GET.get('period', 'tomorrow')
    period_text = 'demain' if period == 'tomorrow' else 'la semaine prochaine'

    # Définir la plage temporelle (7 derniers jours)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    # Récupérer les entrées visuelles
    entries = VisualEntry.objects.filter(
        user=request.user,
        created_at__range=[start_date, end_date]
    ).values('insights').annotate(count=Count('insights')).order_by('-count')

    # Dictionnaire de correspondance des émotions
    emotion_map = {
        1: 'joyeux(se)',
        2: 'triste',
        3: 'en colère',
        4: 'surpris(e)',
        5: 'neutre',
        6: 'stressé(e)',
        7: 'fatigué(e)',
        79: 'calme'
    }

    # Déterminer l'émotion dominante
    dominant_emotion_code = entries[0]['insights'] if entries else 5  # 5 = neutre par défaut
    dominant_emotion = emotion_map.get(dominant_emotion_code, 'neutre')
    emotions = [emotion_map.get(entry['insights'], 'neutre') for entry in entries] or ['neutre']

    # Créer le prompt pour Hugging Face
    prompt = (
        f"Basé sur les émotions récentes de l'utilisateur ({', '.join(emotions)}), "
        f"prédisez son humeur pour {period_text}. Fournissez une courte prédiction (1 phrase), "
        f"un conseil pour améliorer ou maintenir son humeur (1 phrase), "
        f"et une citation motivante liée à l'humeur (1 phrase). "
        "Formattez la réponse comme suit : Prédiction: [votre prédiction]. "
        "Conseil: [votre conseil]. Citation: [votre citation]."
    )

    # Appel API Hugging Face
    api_url = "https://api-inference.huggingface.co/models/distilgpt2"
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_length": 150,
            "num_return_sequences": 1,
            "temperature": 0.7,
            "top_p": 0.9
        }
    }
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        response = requests.post(api_url, json=payload, headers=headers)
        response.raise_for_status()
        ai_data = response.json()
        generated_text = ai_data[0].get('generated_text', '').strip()

        # Extraire la prédiction, le conseil et la citation
        lines = generated_text.split('\n')
        prediction = None
        advice = None
        quote = None
        for line in lines:
            if line.startswith('Prédiction:'):
                prediction = line.replace('Prédiction:', '').strip()
            elif line.startswith('Conseil:'):
                advice = line.replace('Conseil:', '').strip()
            elif line.startswith('Citation:'):
                quote = line.replace('Citation:', '').strip()

        # Valeurs par défaut
        prediction = prediction or f"Votre humeur {period_text} sera probablement {dominant_emotion}."
        advice = advice or "Restez à l'écoute de vos émotions et prenez soin de vous."
        quote = quote or "Chaque jour est une nouvelle opportunité."
    except (requests.RequestException, IndexError, KeyError) as e:
        # Mode secours
        prediction = f"Votre humeur {period_text} sera probablement {dominant_emotion}, basée sur vos tendances récentes."
        advice_dict = {
            'joyeux(se)': [
                "Continuez à partager vos moments de joie ! Essayez une nouvelle activité amusante.",
                "Votre énergie positive est contagieuse, continuez à rayonner !",
                "Organisez une sortie avec des amis pour prolonger ce bonheur."
            ],
            'triste': [
                "Prenez du temps pour vous, peut-être une promenade ou une activité relaxante.",
                "Écoutez votre musique préférée pour remonter le moral.",
                "Parlez à un proche, partager vos sentiments peut alléger votre cœur."
            ],
            'neutre': [
                "Ajoutez une petite aventure à votre journée, comme découvrir un nouveau lieu.",
                "Essayez une nouvelle recette ou un hobby créatif aujourd'hui.",
                "Planifiez un objectif excitant pour donner du peps à votre semaine."
            ],
            'en colère': [
                "Pratiquez une activité apaisante comme la méditation ou l'écriture.",
                "Faites une pause et respirez profondément pour retrouver votre calme.",
                "Essayez un exercice physique pour libérer cette énergie négative."
            ],
            'surpris(e)': [
                "Embrassez l'inattendu ! Notez ce qui vous surprend pour en tirer des leçons.",
                "Partagez cette surprise avec quelqu’un, cela pourrait créer un beau moment.",
                "Utilisez cette énergie pour explorer quelque chose de nouveau."
            ],
            'calme': [
                "Profitez de ce moment de sérénité pour vous ressourcer.",
                "Continuez à cultiver la paix intérieure.",
                "Savourez chaque instant de tranquillité."
            ]
        }
        quotes = {
            'joyeux(se)': [
                "Le bonheur est un parfum que l'on ne peut répandre sans en recevoir quelques gouttes.",
                "Souriez, c'est la clé qui ouvre le cœur de tous.",
                "Le sourire est une lumière qui éclaire les jours sombres."
            ],
            'triste': [
                "Chaque jour est une nouvelle opportunité de trouver du bonheur.",
                "Les larmes d'aujourd'hui arrosent les fleurs de demain.",
                "Même les jours gris finissent par laisser place au soleil."
            ],
            'neutre': [
                "La vie est un mystère à vivre, pas un problème à résoudre.",
                "Chaque pas compte, même les plus petits.",
                "La simplicité est la clé d'une vie équilibrée."
            ],
            'en colère': [
                "La colère est un vent qui souffle, la paix rallume la lumière.",
                "Respirez profondément, la sérénité est à portée de main.",
                "Le calme est une force plus grande que la tempête."
            ],
            'surpris(e)': [
                "L'inattendu est le début d'une nouvelle aventure.",
                "Les surprises de la vie sont des cadeaux déguisés.",
                "Chaque surprise est une chance de grandir."
            ],
            'calme': [
                "Le calme est la clé de la clarté intérieure.",
                "La paix ne vient pas de l’extérieur, elle vient de l’intérieur.",
                "Un esprit tranquille apporte une vie harmonieuse."
            ]
        }
        advice = random.choice(advice_dict.get(dominant_emotion, ["Restez à l'écoute de vos émotions."]))
        quote = random.choice(quotes.get(dominant_emotion, ["Chaque jour est une nouvelle opportunité."]))

    # Réponse JSON
    response_data = {
        'period': period,
        'prediction': prediction,
        'advice': advice,
        'quote': quote,
        'dominant_emotion': dominant_emotion
    }
    return JsonResponse(response_data)

# [Other views remain unchanged unless they also hardcode the token]