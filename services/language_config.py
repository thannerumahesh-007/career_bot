"""
Centralized Multilingual Language Configuration for CareerBot and JARVIS Voice AI.
Defines speech recognition codes, TTS codes, localized labels, and strict AI response instructions.
"""

from typing import Dict, Any, Optional

SUPPORTED_LANGUAGES: Dict[str, Dict[str, Any]] = {
    "en-IN": {
        "code": "en-IN",
        "name": "English (India)",
        "native_name": "English",
        "recognition_code": "en-IN",
        "tts_code": "en-IN",
        "ai_instruction": "Respond entirely in clear, articulate, professional English."
    },
    "en-US": {
        "code": "en-US",
        "name": "English (US)",
        "native_name": "English (US)",
        "recognition_code": "en-US",
        "tts_code": "en-US",
        "ai_instruction": "Respond entirely in clear, professional English."
    },
    "hi-IN": {
        "code": "hi-IN",
        "name": "Hindi (India)",
        "native_name": "हिन्दी",
        "recognition_code": "hi-IN",
        "tts_code": "hi-IN",
        "ai_instruction": (
            "Respond entirely in natural, professional Hindi (हिन्दी) using standard Devanagari script. "
            "Do NOT answer in English. Use clear Hindi terminology with English technical terms transliterated or in parentheses if helpful."
        )
    },
    "te-IN": {
        "code": "te-IN",
        "name": "Telugu (India)",
        "native_name": "తెలుగు",
        "recognition_code": "te-IN",
        "tts_code": "te-IN",
        "ai_instruction": (
            "Respond entirely in natural, fluent Telugu (తెలుగు) using authentic Telugu script. "
            "Do NOT answer in English. Provide complete career guidance and explanations in Telugu."
        )
    },
    "ta-IN": {
        "code": "ta-IN",
        "name": "Tamil (India)",
        "native_name": "தமிழ்",
        "recognition_code": "ta-IN",
        "tts_code": "ta-IN",
        "ai_instruction": (
            "Respond entirely in natural, professional Tamil (தமிழ்) using standard Tamil script. "
            "Do NOT answer in English."
        )
    },
    "kn-IN": {
        "code": "kn-IN",
        "name": "Kannada (India)",
        "native_name": "ಕನ್ನಡ",
        "recognition_code": "kn-IN",
        "tts_code": "kn-IN",
        "ai_instruction": (
            "Respond entirely in natural, professional Kannada (ಕನ್ನಡ) using standard Kannada script. "
            "Do NOT answer in English."
        )
    },
    "ml-IN": {
        "code": "ml-IN",
        "name": "Malayalam (India)",
        "native_name": "മലയാളം",
        "recognition_code": "ml-IN",
        "tts_code": "ml-IN",
        "ai_instruction": (
            "Respond entirely in natural, professional Malayalam (മലയാളം) using standard Malayalam script. "
            "Do NOT answer in English."
        )
    }
}


def get_language_config(code: Optional[str]) -> Dict[str, Any]:
    """Retrieves language configuration, falling back gracefully to en-IN."""
    cfg = None
    if not code:
        cfg = dict(SUPPORTED_LANGUAGES["en-IN"])
    elif code in SUPPORTED_LANGUAGES:
        cfg = dict(SUPPORTED_LANGUAGES[code])
    else:
        prefix = code.split("-")[0].lower()
        for k, v in SUPPORTED_LANGUAGES.items():
            if k.lower().startswith(prefix):
                cfg = dict(v)
                break

    if not cfg:
        cfg = dict(SUPPORTED_LANGUAGES["en-IN"])

    cfg["tts_lang"] = cfg.get("tts_code", "en-IN")
    return cfg


def get_speech_recognition_lang(code: Optional[str]) -> str:
    """Returns the exact BCP-47 recognition code for SpeechRecognition."""
    return get_language_config(code)["recognition_code"]


def get_tts_lang(code: Optional[str]) -> str:
    """Returns the exact TTS language code for SpeechSynthesisUtterance."""
    return get_language_config(code)["tts_code"]


def get_ai_instruction(code: Optional[str]) -> str:
    """Returns the explicit response language instruction for LLM prompts."""
    return get_language_config(code)["ai_instruction"]
