"""Centralised AI service.

Supports Google Gemini (default) or any OpenAI-compatible chat API (Groq, OpenRouter,
a local Ollama server, ...). Configure it in .env - keys are never hard-coded.

Every public method returns validated, structured data or raises AIError, so callers
can fall back to the rule-based logic and label the result accordingly.
"""
import json
import logging
import re

import requests
from flask import current_app

log = logging.getLogger(__name__)

DEFAULT_MODELS = {"gemini": "gemini-2.5-flash", "openai": "gpt-4o-mini"}


class AIError(Exception):
    """Raised when the AI service is unavailable or returns unusable output."""


def _clean_list(value, limit=8, max_len=300):
    if not isinstance(value, list):
        return []
    out = []
    for item in value:
        if isinstance(item, (str, int, float)):
            text = str(item).strip()
            if text:
                out.append(text[:max_len])
        if len(out) >= limit:
            break
    return out


class AIService:
    def __init__(self, provider, api_key, model, base_url="", timeout=40):
        self.provider = provider if provider in DEFAULT_MODELS else "gemini"
        self.api_key = api_key
        self.model = model or DEFAULT_MODELS[self.provider]
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.timeout = timeout

    @property
    def enabled(self):
        return bool(self.api_key)

    @property
    def label(self):
        name = "Gemini" if self.provider == "gemini" else "LLM"
        return f"{name} ({self.model})" if self.enabled else "Rule-based mode"

    # ------------------------------------------------------------------ low level
    def _call(self, prompt):
        if not self.enabled:
            raise AIError("AI is not configured (no AI_API_KEY in .env).")
        try:
            if self.provider == "gemini":
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
                resp = requests.post(
                    url,
                    headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
                    json={"contents": [{"parts": [{"text": prompt}]}],
                          "generationConfig": {"responseMimeType": "application/json", "temperature": 0.4}},
                    timeout=self.timeout,
                )
                resp.raise_for_status()
                return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"model": self.model, "temperature": 0.4,
                      "response_format": {"type": "json_object"},
                      "messages": [{"role": "system", "content": "You reply with valid JSON only."},
                                   {"role": "user", "content": prompt}]},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except requests.Timeout as e:
            raise AIError("The AI service timed out.") from e
        except requests.HTTPError as e:
            code = e.response.status_code if e.response is not None else "?"
            log.warning("AI HTTP error %s", code)
            raise AIError(f"The AI service returned an error (HTTP {code}).") from e
        except (requests.RequestException, KeyError, IndexError, ValueError) as e:
            log.warning("AI request failed: %s", type(e).__name__)
            raise AIError("Could not reach the AI service.") from e

    def _json(self, prompt):
        text = self._call(prompt).strip()
        text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise AIError("The AI response was not valid JSON.") from e
        if not isinstance(data, (dict, list)):
            raise AIError("Unexpected AI response format.")
        return data

    # ------------------------------------------------------------------ features
    def analyze_resume(self, resume_text, detected_skills, role, company, missing_skills):
        """Qualitative feedback + skill-gap recommendations. The numeric score stays rule-based."""
        prompt = f"""You are an experienced technical recruiter reviewing a resume for the role "{role}"{f' at {company}' if company else ''}.
Use ONLY information present in the resume text. Never invent experience, skills or facts.
Skills already detected by a parser: {', '.join(detected_skills) or 'none'}.
Skills from the target profile that were not found: {', '.join(missing_skills) or 'none'}.

Return JSON with exactly these keys:
{{"summary": "2-3 sentence overall assessment",
  "strengths": ["specific strength grounded in the resume", ...],
  "weaknesses": ["specific weakness", ...],
  "suggestions": ["concrete, actionable improvement", ...],
  "recommended_skills": ["skill to learn for this role", ...]}}
Give 3-6 items per list.

RESUME TEXT:
\"\"\"{resume_text[:12000]}\"\"\""""
        data = self._json(prompt)
        if not isinstance(data, dict):
            raise AIError("Unexpected AI response format.")
        result = {
            "summary": str(data.get("summary", "")).strip()[:800],
            "strengths": _clean_list(data.get("strengths")),
            "weaknesses": _clean_list(data.get("weaknesses")),
            "suggestions": _clean_list(data.get("suggestions")),
            "recommended_skills": _clean_list(data.get("recommended_skills"), limit=10, max_len=60),
        }
        if not (result["summary"] or result["strengths"] or result["suggestions"]):
            raise AIError("The AI response was empty.")
        return result

    def generate_questions(self, domain, difficulty, count):
        prompt = f"""Create {count} distinct {difficulty.lower()}-level interview questions for the domain "{domain}" for a fresher / early-career candidate.
Return JSON: {{"questions": [{{"question": "...", "answer": "model answer in 2-4 sentences", "explanation": "why interviewers ask this, 1 sentence"}}]}}"""
        data = self._json(prompt)
        items = data.get("questions") if isinstance(data, dict) else data
        out = []
        for item in items or []:
            if isinstance(item, dict) and item.get("question") and item.get("answer"):
                out.append({"question": str(item["question"]).strip()[:600],
                            "answer": str(item["answer"]).strip()[:2000],
                            "explanation": str(item.get("explanation", "")).strip()[:600]})
        if not out:
            raise AIError("The AI did not return any usable questions.")
        return out[:count]

    def evaluate_answer(self, question, model_answer, user_answer):
        prompt = f"""You are an interviewer. Score the candidate's answer from 0 to 10 for correctness and completeness.
Question: {question}
Reference answer: {model_answer}
Candidate answer: \"\"\"{user_answer[:4000]}\"\"\"
Return JSON: {{"score": integer 0-10, "feedback": "2-3 sentences", "missing_points": ["...", ...]}}"""
        data = self._json(prompt)
        if not isinstance(data, dict):
            raise AIError("Unexpected AI response format.")
        try:
            score = max(0, min(10, int(round(float(data.get("score"))))))
        except (TypeError, ValueError) as e:
            raise AIError("The AI response had no valid score.") from e
        return {"score": score, "feedback": str(data.get("feedback", "")).strip()[:1000],
                "missing_points": _clean_list(data.get("missing_points"), limit=6)}


def get_ai():
    cfg = current_app.config
    return AIService(cfg.get("AI_PROVIDER", "gemini"), cfg.get("AI_API_KEY", ""), cfg.get("AI_MODEL", ""),
                     cfg.get("AI_BASE_URL", ""), cfg.get("AI_TIMEOUT", 40))
