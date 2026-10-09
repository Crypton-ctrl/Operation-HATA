"""
AI Interpretation Layer
Receives structured evidence from the security analysis pipeline (never raw
file bytes) and asks Claude to produce a human-readable security assessment.
AI is explicitly NOT the malware detector - the risk_engine already produced
a score from deterministic evidence; the AI's job is to explain it.

If the AI API is unavailable or unconfigured, a deterministic fallback report
is generated instead so the application never fully depends on the AI layer.
"""
import json
from app.config import get_settings

settings = get_settings()

try:
    import anthropic
    ANTHROPIC_SDK_AVAILABLE = True
except Exception:
    ANTHROPIC_SDK_AVAILABLE = False

SYSTEM_PROMPT = """You are a cybersecurity analyst embedded in "Operation HATA", an \
email-attachment threat analysis platform. You will be given structured, \
machine-collected evidence about an image file (hashes, signature check, \
metadata, entropy, steganography heuristics, embedded/appended data findings, \
YARA matches, OCR text findings, QR code findings, URL heuristics, and a \
pre-computed risk score/category). You do NOT have access to the raw file.

Rules you must follow strictly:
- Never invent findings that are not present in the evidence JSON.
- Distinguish clearly between: Confirmed finding, Suspicious indicator, Unknown, Not detected.
- Explain WHY each significant finding matters and its likely severity.
- Describe a plausible attack scenario ONLY if evidence supports it; otherwise say none is indicated.
- State your confidence level and the limitations of automated analysis.
- Give one clear, actionable recommendation appropriate to the risk category already computed - do not override the numeric score, only interpret it.
- Keep the tone professional, like a SOC analyst report. Be concise but specific.

Respond ONLY with a JSON object with these exact keys (all strings):
{
  "executive_summary": "2-3 sentence high level summary",
  "assessment": "detailed explanation of what was detected and why it matters",
  "likely_scenario": "plausible attack scenario, or 'No specific attack scenario is indicated by current evidence.'",
  "recommendation": "clear recommended action",
  "confidence": "an estimated accuracy percentage (e.g., 90%) - plus a short reason",
  "limitations": "short statement of what this analysis cannot guarantee"
}
No markdown, no code fences, JSON only."""


def _build_user_prompt(evidence: dict, risk_score: int, risk_category: str) -> str:
    payload = {**evidence, "computed_risk_score": risk_score, "computed_risk_category": risk_category}
    return "Structured evidence:\n" + json.dumps(payload, indent=2, default=str)


def generate_ai_report(evidence: dict, risk_score: int, risk_category: str) -> dict:
    if not ANTHROPIC_SDK_AVAILABLE or not settings.AI_API_KEY:
        return _fallback_report(evidence, risk_score, risk_category, reason="AI API key not configured")

    try:
        client = anthropic.Anthropic(api_key=settings.AI_API_KEY)
        message = client.messages.create(
            model=settings.AI_MODEL,
            max_tokens=1200,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _build_user_prompt(evidence, risk_score, risk_category)}],
        )
        raw_text = "".join(block.text for block in message.content if getattr(block, "type", "") == "text")
        cleaned = raw_text.strip().strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
        parsed = json.loads(cleaned)
        return {
            "ai_available": True,
            "executive_summary": parsed.get("executive_summary", ""),
            "assessment": parsed.get("assessment", ""),
            "likely_scenario": parsed.get("likely_scenario", ""),
            "recommendation": parsed.get("recommendation", ""),
            "confidence": parsed.get("confidence", ""),
            "limitations": parsed.get("limitations", ""),
            "raw_model_output": raw_text,
        }
    except Exception as exc:  # noqa: BLE001 - AI must never crash the scan
        return _fallback_report(evidence, risk_score, risk_category, reason=f"AI service error: {exc}")


def _fallback_report(evidence: dict, risk_score: int, risk_category: str, reason: str) -> dict:
    """Deterministic, template-based report generated purely from evidence when
    the AI layer is unavailable. The pipeline and risk score are unaffected."""
    factors = evidence.get("risk_factors", [])
    findings_text = "; ".join(f"{f['factor']} (+{f['points']})" for f in factors) or "No significant findings."

    summary = (
        f"Automated technical analysis classified this attachment as {risk_category} "
        f"risk with a score of {risk_score}/100. AI-based interpretation is unavailable "
        f"({reason}); this report reflects deterministic technical findings only."
    )
    assessment = f"Contributing technical findings: {findings_text}"
    if risk_category in ("HIGH", "CRITICAL"):
        recommendation = ("Keep this attachment quarantined. Do not open it on a production "
                           "system. Investigate the sender and email context before any restoration.")
    elif risk_category == "MEDIUM":
        recommendation = ("Review the specific findings below before deciding whether to release "
                           "this attachment from quarantine. Exercise caution.")
    else:
        recommendation = "No significant threats were identified by the technical analysis modules."

    return {
        "ai_available": False,
        "executive_summary": summary,
        "assessment": assessment,
        "likely_scenario": "Not evaluated (AI interpretation unavailable).",
        "recommendation": recommendation,
        "confidence": "N/A - deterministic fallback",
        "limitations": ("AI analysis unavailable. Technical risk assessment is still available and "
                         "was used to produce this fallback report. " + reason),
        "raw_model_output": None,
    }
