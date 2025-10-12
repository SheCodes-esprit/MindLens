import os
from django.conf import settings
from groq import Groq

def get_groq_client():
    """Initialize Groq client"""
    # Try to get API key from multiple sources
    api_key = getattr(settings, "GROQ_API_KEY", None)
    if not api_key:
        api_key = os.getenv('GROQ_API_KEY')
    
    if not api_key:
        raise ValueError("Groq API key not found. Please add GROQ_API_KEY to your .env file and settings.")
    
    return Groq(api_key=api_key)

def generate_text(prompt, model="llama-3.1-8b-instant", max_tokens=150, temperature=0.7):
    """
    Generate text from Groq using Groq SDK.
    Returns the text, or error message if something fails.
    """
    try:
        client = get_groq_client()
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        # Direct access to the response
        if response.choices and len(response.choices) > 0:
            message_content = response.choices[0].message.content
            if message_content and message_content.strip():
                return message_content.strip()
            else:
                return "Error: Empty response from Groq"
        else:
            return "Error: No choices in response"
            
    except Exception as e:
        return f"Error: {str(e)}"
