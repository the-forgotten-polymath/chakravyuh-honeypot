import re

# Common prompt-injection / bot-detection patterns
SUSPICIOUS_PATTERNS = [
    r"are you a bot",
    r"are you an ai",
    r"are you human",
    r"ignore previous",
    r"system prompt",
    r"developer message",
    r"what model",
    r"chatgpt",
    r"openai",
    r"gemini",
    r"llm",
    r"honeypot",
    r"jailbreak",
]

def is_suspicious(message: str) -> bool:
    msg = message.lower()
    return any(re.search(p, msg) for p in SUSPICIOUS_PATTERNS)
