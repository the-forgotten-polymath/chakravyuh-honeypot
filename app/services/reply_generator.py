import random
import logging
from typing import List, Optional
from app.services.persona_guard import is_suspicious
from app.services.persona_prompt import PERSONA_PROMPT

from app.models.schemas import ScamIntent

logger = logging.getLogger(__name__)

# -----------------------------------
# LLM availability check (Phase 2)
# -----------------------------------
try:
    from app.services.engagement_agent import generate_engagement_reply
    LLM_AVAILABLE = True
except Exception as e:
    LLM_AVAILABLE = False
    logger.warning(f"LLM not available, using fallback only: {e}")


class ReplyGenerator:
    """
    Generate human-like replies to engage scammers.
    Phase 2:
    - LLM-first (Gemini)
    - Rule-based logic as STRICT fallback
    """

    # ----------------------------
    # Rule-based fallback responses
    # ----------------------------

    INITIAL_RESPONSES = [
        "Hello! Thanks for reaching out. What is this about?",
        "Hi there! I got your message. Can you tell me more?",
        "Hey! I'm interested. Please explain more.",
        "Hello! This sounds interesting. What do I need to do?",
        "Arre, thoda samajh nahi aa raha. Batao zara."
    ]

    CURIOUS_RESPONSES = [
        "That sounds interesting. Can you provide more details?",
        "I'm not sure I understand. Can you explain further?",
        "This is new to me. How does it work exactly?",
        "Could you tell me more about this?",
        "Thoda clearly samjhaoge kya?"
    ]

    FINANCIAL_RESPONSES = [
        "What payment method do you accept?",
        "How much do I need to pay?",
        "Can you send me your payment details?",
        "Is there a processing fee involved?",
        "UPI ya bank details share karoge?"
    ]

    PRIZE_RESPONSES = [
        "Really? I won something? That's amazing!",
        "What prize did I win? How do I claim it?",
        "This is exciting! What do I need to do to get my prize?",
        "I didn't enter any contest. Are you sure it's me?",
    ]

    JOB_RESPONSES = [
        "This job sounds perfect! What are the details?",
        "I'm looking for work. What's the salary?",
        "Is this full-time or part-time? What are the requirements?",
        "When can I start? Do I need to pay anything upfront?",
    ]

    STALLING_RESPONSES = [
        "Let me check my account and get back to you.",
        "I need to discuss this with my family first.",
        "Can you give me some time to think about it?",
        "I'm at work right now. Can we continue this later?",
    ]

    ENGAGEMENT_RESPONSES = [
        "Okay, I'm ready. What should I do next?",
        "I understand. Please guide me through the process.",
        "I'm interested in proceeding. What's the next step?",
        "Sounds good. How do we move forward?",
    ]

    # ----------------------------
    # Public methods
    # ----------------------------

    def generate_reply(
        self,
        message: str,
        scam_intents: List[ScamIntent],
        message_count: int,
        session: Optional[object] = None,
    ) -> str:
        """
        Phase-2 logic:
        1) Try Gemini LLM first (if available)
        2) Fall back to rule-based replies if LLM fails
        """
        # 🛡️ Persona guard — deflect suspicion
        if is_suspicious(message):
            return random.choice([
                "Arre, aise kyun pooch rahe ho?",
                "Main samjha nahi, kya matlab?",
                "Aap kaam ki baat batao na.",
                "Mujhe thoda odd lag raha hai ye question.",
            ])


        # 🧠 1️⃣ LLM FIRST
        if LLM_AVAILABLE and session is not None:
            try:
                conversation_history = []

                for m in session.conversation_history:
                    if isinstance(m, dict):
                        conversation_history.append(
                            m.get("text")
                            or m.get("message")
                            or m.get("content")
                            or ""
                        )
                    else:
                        conversation_history.append(
                            getattr(m, "text", "")
                        )


                # Ensure current message is included
                if not conversation_history or conversation_history[-1] != message:
                    conversation_history.append(message)

                llm_reply = generate_engagement_reply(conversation_history)

                if llm_reply and len(llm_reply.strip()) > 2:
                    return llm_reply.strip()

            except Exception as e:
                logger.warning(f"LLM failed, falling back to rules: {e}")

        # 🔁 2️⃣ FALLBACK ONLY
        return self._fallback_reply(
            scam_intents=scam_intents,
            message_count=message_count,
        )

    def generate_goodbye(self) -> str:
        """Natural session ending"""
        endings = [
            "Accha, main thoda check karke batata hoon.",
            "Let me think about it and get back to you.",
            "Abhi thoda busy hoon, baad mein baat karte hain.",
        ]
        return random.choice(endings)

    # ----------------------------
    # Internal fallback logic
    # ----------------------------

    def _fallback_reply(
        self,
        scam_intents: List[ScamIntent],
        message_count: int,
    ) -> str:
        """Original rule-based logic (unchanged behavior)"""

        # First message
        if message_count == 0:
            return random.choice(self.INITIAL_RESPONSES)

        # Early conversation
        if message_count <= 3:
            if ScamIntent.FAKE_PRIZE in scam_intents:
                return random.choice(self.PRIZE_RESPONSES)
            elif ScamIntent.JOB_SCAM in scam_intents:
                return random.choice(self.JOB_RESPONSES)
            else:
                return random.choice(self.CURIOUS_RESPONSES)

        # Mid conversation
        if message_count <= 8:
            if any(intent in scam_intents for intent in [
                ScamIntent.FINANCIAL_FRAUD,
                ScamIntent.UPI_SCAM,
                ScamIntent.FAKE_PRIZE
            ]):
                if random.random() < 0.6:
                    return random.choice(self.FINANCIAL_RESPONSES)

            if random.random() < 0.4:
                return random.choice(self.CURIOUS_RESPONSES)
            else:
                return random.choice(self.ENGAGEMENT_RESPONSES)

        # Late conversation
        if message_count <= 15:
            if random.random() < 0.5:
                return random.choice(self.STALLING_RESPONSES)
            else:
                return random.choice(self.FINANCIAL_RESPONSES)

        # Very late
        return random.choice([
            "I think I need more time to consider this.",
            "Let me verify this information first.",
            "I'll get back to you after checking.",
            "This is taking longer than I expected. Can we pause?",
        ])


# -----------------------------------
# Global instance (used by routes)
# -----------------------------------
reply_generator = ReplyGenerator()
