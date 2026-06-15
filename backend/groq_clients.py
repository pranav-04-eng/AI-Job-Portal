"""Thin wrappers around the three Groq calls the interview loop needs:
speech-to-text (Whisper), chat completion (Llama), and text-to-speech (Orpheus).
All three hit the OpenAI-compatible GroqCloud endpoints via the official SDK.
"""
import os
import base64
from groq import Groq

client = Groq(api_key=os.environ["GROQ_API_KEY"])

# Model IDs verified against console.groq.com (June 2026). The TTS and LLM
# lineups change fairly often, so check the docs if a model 404s.
STT_MODEL = "whisper-large-v3"            # or "whisper-large-v3-turbo" for lower latency
LLM_MODEL = "llama-3.3-70b-versatile"
TTS_MODEL = "canopylabs/orpheus-v1-english"
TTS_VOICE = "troy"                        # try: austin, autumn, troy


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
    response = client.audio.speech.create(
        model=TTS_MODEL,
        voice=TTS_VOICE,
        input=text,
        response_format="wav",
    )
    audio_bytes = response.read()
    return base64.b64encode(audio_bytes).decode("utf-8")
