import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

model = genai.GenerativeModel("models/gemini-2.5-flash")

response = model.generate_content(
    "Reply in casual Hinglish (Hindi + English mix): You won prize. Share UPI ID",
    generation_config={
        "temperature": 0.7,
        "max_output_tokens": 50
    }
)

print("Gemini reply:")
print(response.text)
