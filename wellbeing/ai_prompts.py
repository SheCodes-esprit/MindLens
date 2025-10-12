def create_ai_summary_prompt(record):
    """
    Create a prompt for generating a short, friendly wellness summary.
    """
    return f"""As a friendly wellness assistant, analyze these daily metrics and provide:
1. A brief (1-2 sentence) positive summary
2. 1-2 practical wellness tips

Metrics:
- Mood: {record.mood_score}/10
- Energy: {record.energy_level}/10  
- Sleep: {record.sleep_hours} hours
- Productivity: {record.productivity_score}/10

Please respond in a warm, encouraging tone:"""


def create_ai_recommendation_prompts(record):
    """
    Return a list of (recommendation_type, prompt_text) for different wellbeing areas.
    """
    prompts = []

    # Sleep recommendation
    if record.sleep_hours < 7:
        prompts.append((
            "sleep",
            f"As a sleep coach, suggest one specific, actionable sleep improvement tip for someone who slept only {record.sleep_hours} hours last night. Keep it practical and brief."
        ))

    # Meditation / mindfulness recommendation
    if record.mood_score < 5:
        prompts.append((
            "meditation",
            f"As a mindfulness coach, suggest one quick (5-10 minute) meditation or breathing exercise for someone with low mood (score: {record.mood_score}/10). Make it easy to do immediately."
        ))

    # Exercise recommendation
    if record.energy_level < 5:
        prompts.append((
            "exercise",
            f"Suggest one simple 5-minute exercise or stretch for someone feeling low energy (energy level: {record.energy_level}/10). Focus on gentle movement to boost energy."
        ))

    # Productivity recommendation
    if record.productivity_score < 5:
        prompts.append((
            "productivity",
            f"Suggest one practical productivity technique for someone struggling with focus (productivity score: {record.productivity_score}/10). Make it specific and immediately applicable."
        ))

    return prompts


def generate_summary_and_recommendations(record, model="llama-3.1-8b-instant"):
    """
    Generate a summary and recommendations using the AI utility functions.
    """
    from .ai_utils import generate_text

    results = {
        "summary": "",
        "recommendations": {}
    }

    # Generate summary
    try:
        summary_prompt = create_ai_summary_prompt(record)
        results["summary"] = generate_text(summary_prompt, model=model, max_tokens=200)
    except Exception as e:
        results["summary"] = f"Error generating summary: {e}"

    # Generate recommendations
    try:
        recommendation_prompts = create_ai_recommendation_prompts(record)
        for rec_type, prompt in recommendation_prompts:
            results["recommendations"][rec_type] = generate_text(
                prompt, model=model, max_tokens=100
            )
    except Exception as e:
        results["recommendations"]["error"] = f"Error generating recommendations: {e}"

    return results
