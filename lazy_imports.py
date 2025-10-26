# lazy_imports.py - Charge les modèles seulement quand nécessaire

def get_whisper_model():
    """Charge Whisper seulement quand nécessaire"""
    import whisper
    return whisper.load_model("base")

def get_sentiment_analyzer():
    """Charge NLTK seulement quand nécessaire"""
    import nltk
    from nltk.sentiment import SentimentIntensityAnalyzer
    return SentimentIntensityAnalyzer()

def get_transformers_pipeline():
    """Charge transformers seulement quand nécessaire"""
    from transformers import pipeline
    return pipeline