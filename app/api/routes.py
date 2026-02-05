from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Request, Body
from app.models.schemas import (
    MessageEvent,
    MessageResponse,
    ScamIntent,
    HackathonRequest,
    HackathonResponse,
)
from app.core.security import verify_api_key
from app.services.session_manager import session_manager
from app.services.scam_detector import scam_detector
from app.services.intelligence_extractor import intelligence_extractor
from app.services.reply_generator import reply_generator
from app.services.callback_service import callback_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["honeypot"])


@router.api_route("/honeypot", methods=["GET", "POST", "HEAD"])
async def hackathon_honeypot(
    request_obj: Request,
    api_key: str = Depends(verify_api_key),
    body: Optional[Dict[str, Any]] = Body(default=None),
):
    """
    GUVI Hackathon Honeypot Endpoint (FINAL SAFE VERSION)

    ✔ Accepts GET / POST / HEAD
    ✔ Accepts POST with NO body
    ✔ Accepts POST with {}
    ✔ Accepts POST with valid JSON
    ✔ NEVER returns 422 for empty body
    ✔ Returns ONLY { status, reply }
    """

    # -------------------------
    # GET / HEAD (GUVI tester)
    # -------------------------
    if request_obj.method in ("GET", "HEAD"):
        return {
            "status": "success",
            "reply": "Honeypot API is active",
        }

    # -------------------------
    # POST with no body or {}
    # -------------------------
    if not body:
        return {
            "status": "success",
            "reply": "Hello. How can I help you?",
        }

    # -------------------------
    # Parse HackathonRequest SAFELY
    # -------------------------
    try:
        request = HackathonRequest(**body)
    except Exception as e:
        logger.warning(f"Invalid body received, returning safe response: {e}")
        return {
            "status": "success",
            "reply": "Hello. How can I help you?",
        }

    # -------------------------
    # Session handling
    # -------------------------
    session = session_manager.get_or_create_session(request.sessionId)

    # Add scammer message
    session.add_message("scammer", request.message.text)

    # -------------------------
    # Scam detection (internal)
    # -------------------------
    is_scam, scam_intents, confidence = scam_detector.detect(
        request.message.text
    )

    for intent in scam_intents:
        session.add_scam_intent(intent)
    session.add_confidence_score(confidence)

    # -------------------------
    # Intelligence extraction
    # -------------------------
    intel_report = intelligence_extractor.extract(request.message.text)

    session.intelligence.upiIds.extend(intel_report.upiIds)
    session.intelligence.phoneNumbers.extend(intel_report.phoneNumbers)
    session.intelligence.urls.extend(intel_report.urls)
    session.intelligence.bankDetails.extend(intel_report.bankDetails)
    session.intelligence.emailAddresses.extend(intel_report.emailAddresses)

    # Deduplicate
    session.intelligence.upiIds = list(set(session.intelligence.upiIds))
    session.intelligence.phoneNumbers = list(set(session.intelligence.phoneNumbers))
    session.intelligence.urls = list(set(session.intelligence.urls))
    session.intelligence.bankDetails = list(set(session.intelligence.bankDetails))
    session.intelligence.emailAddresses = list(set(session.intelligence.emailAddresses))

    # -------------------------
    # Termination check
    # -------------------------
    should_terminate, termination_reason = session.should_terminate()

    if should_terminate:
        reply = reply_generator.generate_goodbye()
        session.terminate(termination_reason)

        # Mandatory callback
        await callback_service.send_callback(session)
        callback_service.log_summary(session)

        session_manager.delete_session(request.sessionId)
    else:
        reply = reply_generator.generate_reply(
            message=request.message.text,
            scam_intents=session.scam_intents,
            message_count=session.message_count - 1,
            session=session,
        )

    # Add agent reply
    session.add_message("agent", reply)

    return {
        "status": "success",
        "reply": reply,
    }


# -------------------------------------------------------------------
# LEGACY / INTERNAL ENDPOINTS (UNCHANGED)
# -------------------------------------------------------------------

@router.post("/v1/message", response_model=MessageResponse)
async def process_message(
    event: MessageEvent,
    api_key: str = Depends(verify_api_key),
) -> MessageResponse:

    session = session_manager.get_or_create_session(event.sessionId)
    session.add_message("scammer", event.message)

    is_scam, scam_intents, confidence = scam_detector.detect(event.message)

    for intent in scam_intents:
        session.add_scam_intent(intent)
    session.add_confidence_score(confidence)

    intel_report = intelligence_extractor.extract(event.message)

    session.intelligence.upiIds.extend(intel_report.upiIds)
    session.intelligence.phoneNumbers.extend(intel_report.phoneNumbers)
    session.intelligence.urls.extend(intel_report.urls)
    session.intelligence.bankDetails.extend(intel_report.bankDetails)
    session.intelligence.emailAddresses.extend(intel_report.emailAddresses)

    session.intelligence.upiIds = list(set(session.intelligence.upiIds))
    session.intelligence.phoneNumbers = list(set(session.intelligence.phoneNumbers))
    session.intelligence.urls = list(set(session.intelligence.urls))
    session.intelligence.bankDetails = list(set(session.intelligence.bankDetails))
    session.intelligence.emailAddresses = list(set(session.intelligence.emailAddresses))

    should_terminate, termination_reason = session.should_terminate()

    if should_terminate:
        reply = reply_generator.generate_goodbye()
        should_continue = False
        session.terminate(termination_reason)

        await callback_service.send_callback(session)
        callback_service.log_summary(session)
        session_manager.delete_session(event.sessionId)
    else:
        reply = reply_generator.generate_reply(
            event.message,
            session.scam_intents,
            session.message_count - 1,
        )
        should_continue = True

    session.add_message("agent", reply)

    return MessageResponse(
        sessionId=event.sessionId,
        reply=reply,
        scamDetected=is_scam,
        scamIntents=scam_intents if scam_intents else [ScamIntent.NONE],
        confidence=confidence,
        shouldContinue=should_continue,
        extractedIntelligence={
            "upiIds": intel_report.upiIds,
            "phoneNumbers": intel_report.phoneNumbers,
            "urls": intel_report.urls,
            "bankDetails": intel_report.bankDetails,
            "emailAddresses": intel_report.emailAddresses,
        },
    )


@router.get("/v1/health")
async def health_check():
    return {
        "status": "healthy",
        "active_sessions": session_manager.get_active_session_count(),
    }


@router.post("/v1/cleanup")
async def cleanup_sessions(api_key: str = Depends(verify_api_key)):
    session_manager.cleanup_expired_sessions()
    return {
        "status": "success",
        "active_sessions": session_manager.get_active_session_count(),
    }
