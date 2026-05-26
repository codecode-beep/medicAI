import json
import logging
from typing import Any

import google.generativeai as genai

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger("medintel")


class GeminiService:
    def __init__(self) -> None:
        if settings.gemini_api_key:
            genai.configure(api_key=settings.gemini_api_key)
        self.model_name = settings.gemini_model
        self.vision_model_name = settings.gemini_vision_model

    def _get_model(self, vision: bool = False):
        name = self.vision_model_name if vision else self.model_name
        return genai.GenerativeModel(name)

    async def analyze_text(self, text: str, context: str = "") -> dict[str, Any]:
        prompt = f"""You are a medical AI assistant. Analyze the following medical document and return valid JSON.

{context}

Document content:
{text[:15000]}

Return ONLY valid JSON with these fields:
{{
  "summary": "brief summary in plain language",
  "findings": ["list of key findings"],
  "medicines": [{{"name": "", "dosage": "", "frequency": ""}}],
  "conditions": ["possible conditions identified"],
  "severity": "low|moderate|high|critical",
  "recommendations": ["actionable recommendations"],
  "interpretation": "detailed medical interpretation",
  "lab_values": [{{"name": "", "value": "", "unit": "", "status": "normal|abnormal"}}]
}}

IMPORTANT: This is for informational purposes only, not a medical diagnosis."""

        try:
            model = self._get_model()
            response = model.generate_content(prompt)
            result = self._parse_json_response(response.text)
            return self._normalize_analysis(result)
        except Exception as e:
            logger.error("Gemini text analysis failed: %s", e)
            return self._fallback_analysis(text, str(e))

    async def analyze_image(self, image_bytes: bytes, mime_type: str, context: str = "") -> dict[str, Any]:
        prompt = f"""You are MedIntel AI, a medical document and imaging analyst.

Analyze this image carefully. It may be:
- Handwritten or printed PRESCRIPTION
- Blood test / lab report (photo or scan)
- Hospital or clinic medical report
- X-ray, MRI, CT scan, ultrasound
- Any other clinical document

{context}

Instructions:
1. Identify what type of document this is (document_type field).
2. If it is a PRESCRIPTION (handwritten or printed): read ALL visible medicine names, doses, frequency, and duration. Transcribe handwriting as best you can; note uncertain words with "(unclear)".
3. If it is a LAB REPORT: extract key values and abnormal results.
4. If it is IMAGING (X-ray/MRI/CT): describe radiological findings.
5. Always fill medicines array when any drugs are visible — never leave empty for prescriptions.

Return ONLY valid JSON:
{{
  "document_type": "prescription_handwritten|prescription_printed|lab_report|medical_report|x-ray|mri|ct|ultrasound|other",
  "summary": "brief summary in plain language",
  "findings": ["list of key findings from the document"],
  "medicines": [{{"name": "medicine name", "dosage": "dose if visible", "frequency": "how often if visible"}}],
  "conditions": ["conditions or symptoms mentioned"],
  "severity": "low|moderate|high|critical|unknown",
  "recommendations": ["actionable recommendations"],
  "interpretation": "detailed interpretation appropriate to document type",
  "handwriting_notes": "note if handwriting was hard to read, or null"
}}

Use severity "unknown" only if severity cannot be inferred. For prescriptions, severity is usually low unless urgent/warning language is visible.

IMPORTANT: Informational only — not a medical diagnosis. Do NOT refuse analysis because the document is handwritten."""

        try:
            model = self._get_model(vision=True)
            image_part = {"mime_type": mime_type, "data": image_bytes}
            response = model.generate_content([prompt, image_part])
            result = self._parse_json_response(response.text)
            return self._normalize_analysis(result)
        except Exception as e:
            logger.error("Gemini vision analysis failed: %s", e)
            return self._fallback_analysis("Medical image uploaded", str(e))

    async def chat(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
        rag_context: str = "",
    ) -> str:
        system_prompt = """You are MedIntel AI, a personalized medical intelligence assistant.
You help users understand their medical reports, scans, prescriptions, and health history.
Be conversational, empathetic, and clear. Use plain language.
Always remind users to consult healthcare professionals for medical decisions.

"""
        if rag_context:
            system_prompt += f"\nRelevant medical history context:\n{rag_context}\n"

        try:
            model = self._get_model()
            if history:
                gemini_history = []
                for h in history[-10:]:
                    content = (h.get("content") or "").strip()
                    if not content or "Gemini API error" in content:
                        continue
                    role = "model" if h.get("role") in ("assistant", "model") else "user"
                    gemini_history.append({"role": role, "parts": [content]})
                chat = model.start_chat(history=gemini_history)
                response = chat.send_message(f"{system_prompt}\nUser: {message}")
            else:
                full_message = system_prompt + f"\nUser: {message}"
                response = model.generate_content(full_message)
            return response.text or "I could not generate a response. Please try again."
        except Exception as e:
            logger.error("Gemini chat failed: %s", e)
            err = str(e)
            if "429" in err:
                hint = "quota exceeded — try gemini-2.5-flash or check billing at https://ai.google.dev"
            elif "API_KEY" in err.upper() or "401" in err or "403" in err:
                hint = "check GEMINI_API_KEY in backend/.env"
            elif "Role" in err and "not supported" in err:
                hint = "chat history error (retrying should work after server reload)"
            else:
                hint = f"request failed ({err[:120]})"
            return f"I'm sorry, I couldn't process that: {hint}"

    async def compare_reports(self, report_a: dict, report_b: dict) -> dict[str, Any]:
        prompt = f"""Compare these two medical reports and identify changes, trends, and concerns.

Report A ({report_a.get('title', 'Report A')}):
Summary: {report_a.get('ai_summary', '')}
Findings: {json.dumps(report_a.get('ai_findings', {}))}
Conditions: {json.dumps(report_a.get('conditions', []))}
Medicines: {json.dumps(report_a.get('medicines', []))}

Report B ({report_b.get('title', 'Report B')}):
Summary: {report_b.get('ai_summary', '')}
Findings: {json.dumps(report_b.get('ai_findings', {}))}
Conditions: {json.dumps(report_b.get('conditions', []))}
Medicines: {json.dumps(report_b.get('medicines', []))}

Return ONLY valid JSON:
{{
  "summary": "comparison summary",
  "improvements": ["areas that improved"],
  "concerns": ["areas of concern"],
  "trend_analysis": "detailed trend analysis",
  "recommendations": ["recommendations based on comparison"]
}}"""

        try:
            model = self._get_model()
            response = model.generate_content(prompt)
            return self._parse_json_response(response.text)
        except Exception as e:
            logger.error("Report comparison failed: %s", e)
            return {"summary": "Unable to compare reports at this time.", "error": str(e)}

    async def generate_embedding(self, text: str) -> list[float]:
        try:
            result = genai.embed_content(
                model=settings.gemini_embedding_model,
                content=text,
                task_type="retrieval_document",
            )
            return result["embedding"]
        except Exception as e:
            logger.error("Embedding generation failed: %s", e)
            return [0.0] * 768

    def _parse_json_response(self, text: str) -> dict[str, Any]:
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            text = text.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"summary": text, "findings": [], "medicines": [], "conditions": [], "severity": "unknown"}

    def _normalize_analysis(self, result: dict[str, Any]) -> dict[str, Any]:
        """Clean AI output for UI and database."""
        medicines = result.get("medicines") or []
        if isinstance(medicines, list):
            cleaned = []
            for med in medicines:
                if isinstance(med, dict) and (med.get("name") or "").strip():
                    cleaned.append({
                        "name": str(med.get("name", "")).strip(),
                        "dosage": med.get("dosage") or "",
                        "frequency": med.get("frequency") or "",
                    })
            result["medicines"] = cleaned

        severity = str(result.get("severity", "unknown")).lower().strip()
        if severity in ("not applicable", "n/a", "na", "none", ""):
            severity = "unknown"
        result["severity"] = severity

        # Merge document_type into findings if useful
        doc_type = result.get("document_type")
        if doc_type and doc_type not in ("other", "x-ray", "mri", "ct", "ultrasound"):
            findings = list(result.get("findings") or [])
            label = doc_type.replace("_", " ").title()
            if not any(label.lower() in str(f).lower() for f in findings):
                findings.insert(0, f"Document type: {label}")
            result["findings"] = findings

        return result

    def _fallback_analysis(self, text: str, error: str | None = None) -> dict[str, Any]:
        hint = "Check Gemini API quota/billing at https://ai.google.dev"
        if error and "429" in error:
            hint = "Gemini quota exceeded. Try gemini-2.5-flash or enable billing in Google AI Studio."
        elif error and ("API_KEY" in error.upper() or "401" in error or "403" in error):
            hint = "Invalid or missing GEMINI_API_KEY in backend/.env"
        return {
            "summary": f"Document received ({len(text)} characters). AI analysis unavailable: {hint}",
            "findings": [hint],
            "medicines": [],
            "conditions": [],
            "severity": "unknown",
            "recommendations": [hint],
            "interpretation": hint,
        }


gemini_service = GeminiService()
