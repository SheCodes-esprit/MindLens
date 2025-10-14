from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import VisualEntryForm
from .models import VisualEntry, VisualInsight
from transformers import DetrImageProcessor, DetrForObjectDetection
from PIL import Image
import torch
import cv2  # Pour vidéos
from colorthief import ColorThief
from django.conf import settings
import os

@login_required
def visual_list(request):
    entries = VisualEntry.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'frontoffice/pages/visual/visual_list.html', {'entries': entries})

@login_required
def visual_detail(request, pk):
    entry = get_object_or_404(VisualEntry, pk=pk, user=request.user)
    insights = entry.insights.all()
    return render(request, 'frontoffice/pages/visual/visual_detail.html', {'entry': entry, 'insights': insights})

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
@login_required
def visual_delete(request, pk):
    entry = get_object_or_404(VisualEntry, pk=pk, user=request.user)
    if request.method == 'POST':
        entry.delete()
        return redirect('visual_list')
    return render(request, 'frontoffice/pages/visual/visual_confirm_delete.html', {'entry': entry})

def analyze_visual(entry):
    # Charger modèle Hugging Face (gratuit, local)
    processor = DetrImageProcessor.from_pretrained("facebook/detr-resnet-50")
    model = DetrForObjectDetection.from_pretrained("facebook/detr-resnet-50")

    file_path = os.path.join(settings.MEDIA_ROOT, entry.media_url.name)

    # Gérer vidéo : extraire frame milieu
    if entry.type == 'video':
        cap = cv2.VideoCapture(file_path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, cap.get(cv2.CAP_PROP_FRAME_COUNT) // 2)
        ret, frame = cap.read()
        if ret:
            image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        cap.release()
    else:
        image = Image.open(file_path).convert("RGB")

    # Détection objets
    inputs = processor(images=image, return_tensors="pt")
    outputs = model(**inputs)
    target_sizes = torch.tensor([image.size[::-1]])
    results = processor.post_process_object_detection(outputs, threshold=0.5, target_sizes=target_sizes)[0]
    detected_objects = [model.config.id2label[label.item()] for label in results["labels"]]

    # Couleurs dominantes (gratuit avec ColorThief)
    color_thief = ColorThief(file_path)
    dominant_colors = color_thief.get_palette(color_count=3)

    # Détection émotion (simplifiée; étendez avec un modèle comme 'j-hartmann/emotion-english-distilroberta-base' si texte extrait)
    emotion = 'neutral'
    if any(obj in ['person', 'face', 'smile'] for obj in detected_objects):
        emotion = 'happy'  # Règle basique; améliorez avec OCR + sentiment si besoin

    # Tags générés
    tags_generated = detected_objects[:5]  # Top 5 comme tags

    # Confidence moyenne
    ai_confidence = sum(results["scores"].tolist()) / len(results["scores"]) if len(results["scores"]) > 0 else 0.0

    # Sauvegarde
    entry.ai_description = f"Détecté: {', '.join(detected_objects)}. Émotion: {emotion}."
    entry.save()

    VisualInsight.objects.create(
        visual_entry=entry,
        detected_objects=detected_objects,
        dominant_colors=dominant_colors,
        emotion_detected=emotion,
        tags_generated=tags_generated,
        ai_confidence=ai_confidence
    )