"""Thin wrappers around the Groq calls our services need:
speech-to-text (Whisper), chat completion (Llama), and text-to-speech (Orpheus).
All hit the OpenAI-compatible GroqCloud endpoints via the official SDK.

Shared by interview-service (STT/LLM/TTS) and screening-service (LLM only).
"""
import base64

from groq import Groq, BadRequestError

from common.config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)

# Model IDs verified against console.groq.com (June 2026). The TTS and LLM
# lineups change fairly often, so check the docs if a model 404s.
STT_MODEL = "whisper-large-v3"            # or "whisper-large-v3-turbo" for lower latency
LLM_MODEL = "llama-3.3-70b-versatile"
TTS_MODEL = "canopylabs/orpheus-v1-english"
TTS_VOICE = "troy"                        # try: austin, autumn, troy


class TTSModelTermsRequired(RuntimeError):
    """Raised when the configured TTS model requires terms acceptance."""


def transcribe(audio_bytes: bytes, filename: str = "answer.webm") -> str:
    """Candidate's recorded answer (webm/wav/mp3...) -> text."""
    result = client.audio.transcriptions.create(
        file=(filename, audio_bytes),
        model=STT_MODEL,
    )
    return result.text.strip()


def chat(messages: list, json_mode: bool = False) -> str:
    """Single LLM call. Set json_mode=True to force a JSON object back."""
    kwargs = {"model": LLM_MODEL, "messages": messages, "temperature": 0.6}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content


def synthesize(text: str) -> str:
    """Text -> base64-encoded WAV audio (data the browser can play directly)."""
    try:
        response = client.audio.speech.create(
            model=TTS_MODEL,
            voice=TTS_VOICE,
            input=text,
            response_format="wav",
        )
    except BadRequestError as exc:
        msg = str(exc)
        if "model_terms_required" in msg or "requires terms acceptance" in msg:
            raise TTSModelTermsRequired(
                f"TTS model '{TTS_MODEL}' requires terms acceptance in Groq Console."
            ) from exc
        raise

    audio_bytes = response.read()
    return base64.b64encode(audio_bytes).decode("utf-8")
