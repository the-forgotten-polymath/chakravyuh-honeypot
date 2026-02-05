import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

print("GOOGLE_API_KEY =", os.getenv("GOOGLE_API_KEY"))

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

print("\nAvailable Gemini models:\n")

for model in genai.list_models():
    if "generateContent" in model.supported_generation_methods:
        print(model.name)
