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
        prompt = f"""You are a medical AI assistant. Analyze the following medical document and return aits JSON.

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
            return self._parse_json_response(response.text)
        except Exception as e:
            logger.error("Gemini text analysis failed: %s", e)
            return self._fallback_analysis(text, str(e))

    async def analyze_image(self, image_bytes: bytes, mime_type: str, context: str = "") -> dict[str, Any]:
        prompt = f"""You are a medical imaging AI assistant. Analyze this medical image (X-ray, MRI, CT scan, or other medical image).

{context}

Return ONLY valid JSON with these fields:
{{
  "summary": "brief summary in plain language",
  "findings": ["list of imaging findings"],
  "medicines": [],
  "conditions": ["possible conditions suggested by imaging"],
  "severity": "low|moderate|high|critical",
  "recommendations": ["recommended follow-up actions"],
  "interpretation": "detailed radiological interpretation",
  "image_type": "x-ray|mri|ct|ultrasound|other"
}}

IMPORTANT: This is for informational purposes only, not a medical diagnosis."""

        try:
            model = self._get_model(vision=True)
            image_part = {"mime_type": mime_type, "data": image_bytes}
            response = model.generate_content([prompt, image_part])
            return self._parse_json_response(response.text)
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

        full_message = system_prompt + f"\nUser: {message}"

        try:
            model = self._get_model()
            if history:
                chat = model.start_chat(history=[{"role": h["role"], "parts": [h["content"]]} for h in history[-10:]])
                response = chat.send_message(full_message)
            else:
                response = model.generate_content(full_message)
            return response.text
        except Exception as e:
            logger.error("Gemini chat failed: %s", e)
            return (
                "Gemini API error: "
                + (
                    "quota exceeded — try gemini-2.5-flash or check billing at https://ai.google.dev"
                    if "429" in str(e)
                    else "check GEMINI_API_KEY and model settings in backend/.env"
                )
            )

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
