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
import os
from fer import FER
import numpy as np
from moviepy.editor import VideoFileClip
from io import BytesIO

# ----------------------  STATISTIQUES ----------------------

from django.db.models import Count, Avg
from django.db.models.functions import TruncDay
from django.http import JsonResponse
from django.views.decorators.cache import cache_page
from datetime import date, timedelta
from django.db.models.functions import TruncWeek

# ---------------------- LIST & DETAIL ----------------------

@login_required
def visual_list(request):
    entries = VisualEntry.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'frontoffice/pages/visual/visual_list.html', {'entries': entries})


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
    return JsonResponse({'series': series})
