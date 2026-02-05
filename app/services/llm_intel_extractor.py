import os
import json
import google.generativeai as genai

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

model = genai.GenerativeModel("models/gemini-2.5-flash")

INTEL_PROMPT = """
You are an intelligence extraction agent.

From the message below, extract ONLY these fields if present:
- upi_ids
- phone_numbers
- urls
- bank_names

Rules:
- Return STRICT JSON only
- Use empty arrays if nothing found
- Do not add explanations

Message:
"""

def extract_intel_llm(message: str) -> dict:
    response = model.generate_content(
        INTEL_PROMPT + message,
        generation_config={
            "temperature": 0,
            "max_output_tokens": 120
        }
    )

    try:
        return json.loads(response.text)
    except Exception:
        return {
            "upi_ids": [],
            "phone_numbers": [],
            "urls": [],
            "bank_names": []
        }
