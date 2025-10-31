# MindLens – AI-Powered Multimodal Journaling App

**MindLens** is a **Django 4.2** full-stack application that transforms personal journaling using **text, audio, visuals, and wellness data** — all enhanced by **AI insights** for emotional awareness, productivity, and mental well-being.

---

## 0. Gestion Utilisateur (User Management)

### Entités
- **User** : `id`, `email`, `password_hash`, `username`, `created_at`, `avatar_url`, `bio`, `preferences`, `timezone`

### Relation
- **1 User → 1 UserProfile**

### AI Insights
- Personnalisation des conseils/journaux selon préférences
- Détection du style d’interaction préféré (coach, ami, neutre)
- Suggestions d’horaires optimaux pour journaling selon habitudes

### APIs externes utiles
- **Gravatar API** → avatar automatique via email  
- **ip-api / ipinfo.io** (Free Tier) → détection de timezone/localisation  
- **Firebase Authentication** (Free tier) → login sécurisé  
- **Auth0** (Free plan) → connexions sociales (Google, Facebook…)

---

## 1. Gestion Audio Journaling

### Entités
- **AudioEntry** : `id`, `user_id`, `title`, `audio_url`, `duration`, `ai_transcript`, `created_at`  
- **AudioEmotionAnalysis** : `id`, `audio_entry_id` (FK), `detected_emotion`, `intensity`, `ai_model_version`, `created_at`

### Relation
- **1 AudioEntry → plusieurs AudioEmotionAnalysis**

### AI Insights
- Transcription vocale automatique (speech-to-text)
- Détection émotionnelle (joie, tristesse, stress…)
- Résumé de l’entrée audio
- Graphique de l’évolution des émotions dans le temps

### APIs externes utiles
- **OpenAI Whisper** (local ou API) → transcription  
- **AssemblyAI** (Free tier) → transcription + émotions  
- **Google Cloud Speech-to-Text** (Free credits) → haute précision  
- **IBM Watson Tone Analyzer** (Lite) → analyse émotionnelle vocale

---

## 2. Gestion Visual (Images/Vidéos) Journaling

### Entités
- **VisualEntry** : `id`, `user_id`, `type` (image/video), `media_url`, `caption`, `ai_description`, `created_at`  
- **VisualInsight** : `id`, `visual_entry_id` (FK), `detected_objects`, `dominant_colors`, `emotion_detected`, `tags_generated`, `ai_confidence`

### Relation
- **1 VisualEntry → plusieurs VisualInsight**

### AI Insights
- Reconnaissance d’objets, visages, scènes
- Détection d’ambiance émotionnelle (photo sombre = tristesse possible)
- Génération automatique de légendes
- Extraction de mots-clés pour indexer les souvenirs

### APIs externes utiles
- **Google Vision API** (Free credits) → objets, visages, texte  
- **Microsoft Azure Computer Vision** (Free tier) → tags & descriptions  
- **Clarifai** (Free plan) → émotions, scènes  
- **HuggingFace Models** (self-hosted) → vision multimodale

---

## 3. Gestion Text Journaling

### Entités
- **TextEntry**  
  - `id`, `user_id` (FK), `content`, `ai_summary`, `sentiment_overall`, `created_at`  
- **TextInsight**  
  - `id`, `text_entry_id` (FK), `key_topics` (JSON), `stress_level` (0–1), `writing_style` (JSON), `ai_advice`, `created_at`

### Relation
- **1 TextEntry → plusieurs TextInsight**  
  *(plusieurs modèles d’analyse sur la même note)*

### AI Insights
- Résumé automatique du texte
- Analyse thématique : sujets récurrents (stress, relations, objectifs)
- Analyse du style d’écriture : clarté, expressivité
- Recommandations personnalisées

### APIs externes utiles
- **HuggingFace Transformers** (self-hosted) → sentiment, thèmes  
- **OpenAI GPT** (Playground/API) → résumé & conseils  
- **MeaningCloud** (Free tier) → analyse de sentiment  
- **TextRazor / ParallelDots** → entités, keywords

---

## 4. Gestion Well-being & Productivity

### Entités
- **WellbeingRecord** : `id`, `user_id`, `date`, `mood_score`, `energy_level`, `sleep_hours`, `productivity_score`, `ai_summary`  
- **RoutineRecommendation** : `id`, `wellbeing_record_id` (FK), `type`, `description`, `ai_generated`, `efficiency_score`, `created_at`

### Relation
- **1 WellbeingRecord → plusieurs RoutineRecommendation**

### AI Insights
- Corrélation humeur ↔ productivité
- Détection des tendances (burnout, amélioration)
- Suggestions de routines : sport, méditation, nutrition
- Prédictions d’évolution du bien-être

### APIs externes utiles
- **Fitbit API** (Free OAuth) → sommeil, activité  
- **Google Fit / Apple HealthKit** → données santé  
- **OpenMeteo API** (Free) → météo ↔ humeur  
- **MoodPanda** → tracking d’humeur

---

## Tech Stack

- **Backend**: Django 4.2 (Python)  
- **Database**: PostgreSQL / SQLite  
- **AI**: Hugging Face, local models, free-tier APIs  
- **Frontend**: HTML/CSS/JS (extendable with React/Vue)  
- **Storage**: Django `FileField` + Cloudinary/S3 (optional)

---

## Setup & Installation

```bash
git clone https://github.com/SheCodes-esprit/MindLens.git
cd MindLens
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
