import os
import google.generativeai as genai
from app.services.persona_prompt import PERSONA_PROMPT

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

model = genai.GenerativeModel(
    model_name="models/gemini-2.5-flash",
    system_instruction=PERSONA_PROMPT
)

def generate_engagement_reply(conversation_history: list[str]) -> str:
    prompt = (
        "Reply in casual Hinglish, WhatsApp style.\n\n"
        + "\n".join(conversation_history[-6:])
    )

    response = model.generate_content(
        prompt,
        generation_config={
            "temperature": 0.7,
            "max_output_tokens": 180
        }
    )

    return response.text.strip()
