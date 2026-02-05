import re
import json
import logging
from typing import List
import os

import google.generativeai as genai

from app.models.schemas import IntelligenceReport

logger = logging.getLogger(__name__)

# ----------------------------
# Gemini LLM setup (silent)
# ----------------------------
LLM_AVAILABLE = False
try:
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    llm_model = genai.GenerativeModel("models/gemini-2.5-flash")
    LLM_AVAILABLE = True
except Exception as e:
    logger.warning(f"LLM intel extractor disabled: {e}")


class IntelligenceExtractor:
    """
    Hybrid intelligence extractor:
    - Regex (fast, deterministic)
    - LLM enrichment (bank names, implicit info)
    """

    # ----------------------------
    # Regex patterns
    # ----------------------------
    UPI_PATTERN = r'\b([a-zA-Z0-9._-]+@[a-zA-Z]+)\b'
    PHONE_PATTERN = r'\b(?:\+91|91)?[-.\s]?([6-9]\d{9})\b'
    URL_PATTERN = r'https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)'
    BANK_PATTERN = r'\b(?:account|a/c|ac)(?:\s+no\.?|\s+number)?\s*:?\s*(\d{9,18})\b'
    EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

    # ----------------------------
    # Public API
    # ----------------------------
    def extract(self, message: str) -> IntelligenceReport:
        """Extract intelligence from a message (regex + LLM)"""

        report = IntelligenceReport()

        # ----------------------------
        # Regex extraction
        # ----------------------------
        report.upiIds = list(set(re.findall(self.UPI_PATTERN, message, re.IGNORECASE)))
        report.phoneNumbers = list(set(re.findall(self.PHONE_PATTERN, message)))
        report.urls = list(set(re.findall(self.URL_PATTERN, message, re.IGNORECASE)))
        report.bankDetails = list(set(re.findall(self.BANK_PATTERN, message, re.IGNORECASE)))

        email_matches = re.findall(self.EMAIL_PATTERN, message)
        report.emailAddresses = list(
            set(e for e in email_matches if not self._is_upi_id(e))
        )
        logger.info(f"INTEL EXTRACTED: {report}")


        # ----------------------------
        # LLM enrichment (silent)
        # ----------------------------
        if LLM_AVAILABLE:
            try:
                llm_intel = self._extract_with_llm(message)

                report.upiIds.extend(llm_intel.get("upiIds", []))
                report.phoneNumbers.extend(llm_intel.get("phoneNumbers", []))
                report.urls.extend(llm_intel.get("urls", []))
                report.bankDetails.extend(llm_intel.get("bankDetails", []))

            except Exception as e:
                logger.warning(f"LLM intel extraction failed: {e}")

        # Deduplicate again
        report.upiIds = list(set(report.upiIds))
        report.phoneNumbers = list(set(report.phoneNumbers))
        report.urls = list(set(report.urls))
        report.bankDetails = list(set(report.bankDetails))
        report.emailAddresses = list(set(report.emailAddresses))

        return report

    # ----------------------------
    # Internal helpers
    # ----------------------------
    def _extract_with_llm(self, message: str) -> dict:
        """
        Use Gemini to extract subtle intelligence.
        Returns plain dict, never raises outward.
        """

        prompt = f"""
Extract scam intelligence from the message below.

Return ONLY valid JSON with these keys:
- upiIds
- phoneNumbers
- urls
- bankDetails

Rules:
- Use arrays for all fields
- Use empty arrays if nothing found
- Do NOT add explanation text

Message:
\"\"\"{message}\"\"\"
"""

        response = llm_model.generate_content(
            prompt,
            generation_config={
                "temperature": 0,
                "max_output_tokens": 150
            }
        )

        try:
            return json.loads(response.text)
        except Exception:
            return {
                "upiIds": [],
                "phoneNumbers": [],
                "urls": [],
                "bankDetails": []
            }

    def _is_upi_id(self, email: str) -> bool:
        """Check if an email-like string is actually a UPI ID"""
        upi_handles = [
            'paytm', 'oksbi', 'ybl', 'apl',
            'axl', 'ibl', 'icici', 'okhdfc'
        ]
        domain = email.split('@')[-1].lower()
        return any(handle in domain for handle in upi_handles)

    def merge_reports(self, reports: List[IntelligenceReport]) -> IntelligenceReport:
        """Merge multiple intelligence reports"""

        merged = IntelligenceReport()

        for r in reports:
            merged.upiIds.extend(r.upiIds)
            merged.phoneNumbers.extend(r.phoneNumbers)
            merged.urls.extend(r.urls)
            merged.bankDetails.extend(r.bankDetails)
            merged.emailAddresses.extend(r.emailAddresses)

        merged.upiIds = list(set(merged.upiIds))
        merged.phoneNumbers = list(set(merged.phoneNumbers))
        merged.urls = list(set(merged.urls))
        merged.bankDetails = list(set(merged.bankDetails))
        merged.emailAddresses = list(set(merged.emailAddresses))

        return merged


# Global extractor instance
intelligence_extractor = IntelligenceExtractor()
