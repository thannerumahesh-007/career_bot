import os
import logging
from dotenv import load_dotenv
import requests
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

# Selected JARVIS Voice ID (premade conversational voice)
DEFAULT_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
DEFAULT_MODEL_ID = "eleven_turbo_v2_5"


class ElevenLabsService:
    def __init__(self):
        self.api_url = "https://api.elevenlabs.io/v1"

    def _get_api_key(self) -> str:
        load_dotenv(override=True)
        return os.getenv("ELEVENLABS_API_KEY", "").strip()

    def _get_voice_id(self) -> str:
        load_dotenv(override=True)
        voice_id = os.getenv("ELEVENLABS_VOICE_ID", "").strip()
        return voice_id if voice_id else DEFAULT_VOICE_ID

    def _get_model_id(self) -> str:
        load_dotenv(override=True)
        model_id = os.getenv("ELEVENLABS_MODEL_ID", "").strip()
        return model_id if model_id else DEFAULT_MODEL_ID

    def is_configured(self) -> bool:
        key = self._get_api_key()
        return bool(key and key != "your_elevenlabs_api_key_here")

    def text_to_speech(self, text: str) -> Tuple[Optional[bytes], str, Optional[str]]:
        """
        Converts text to speech using ElevenLabs API with selected voice ID wWWn96OtTHu1sn8SRGEr.
        Returns: (audio_bytes, content_type, error_message)
        """
        if not text or not text.strip():
            return None, "", "Text content for speech generation is empty."

        if not self.is_configured():
            return (
                None,
                "",
                "ElevenLabs API key is not configured. Please set ELEVENLABS_API_KEY in your .env file.",
            )

        api_key = self._get_api_key()
        voice_id = self._get_voice_id()
        model_id = self._get_model_id()

        endpoint = f"{self.api_url}/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        # Optimized for natural, human-like conversational delivery:
        # - Natural pacing & pauses
        # - High vocal fidelity & clear pronunciation
        # - Calm, intelligent JARVIS demeanor without artificial artifacts
        payload = {
            "text": text.strip(),
            "model_id": model_id,
            "voice_settings": {
                "stability": 0.50,
                "similarity_boost": 0.85,
                "style": 0.0,
                "use_speaker_boost": True,
            },
        }

        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=25,
            )

            if response.status_code == 200:
                return response.content, "audio/mpeg", None

            # Handle common ElevenLabs error responses
            try:
                error_data = response.json()
                detail = error_data.get("detail", {})
                if isinstance(detail, dict):
                    err_message = detail.get("message", response.text)
                else:
                    err_message = str(detail)
            except Exception:
                err_message = response.text

            if "API key ID used as API key" in err_message or not api_key.startswith("sk_"):
                return (
                    None,
                    "",
                    "ElevenLabs key notice: An API Key ID was provided instead of the secret key (ElevenLabs API keys begin with 'sk_').",
                )
            elif response.status_code == 401 or "invalid_api_key" in str(error_data):
                return (
                    None,
                    "",
                    "ElevenLabs authentication failed. Your API key appears to be invalid.",
                )
            elif response.status_code == 402 or "paid_plan_required" in str(error_data):
                return (
                    None,
                    "",
                    f"ElevenLabs Plan Limitation: Voice ID '{voice_id}' is a Voice Library voice requiring an ElevenLabs paid subscription for API access.",
                )
            elif response.status_code == 429:
                return (
                    None,
                    "",
                    "ElevenLabs quota exceeded or rate limit reached. Please check your account credits.",
                )
            elif response.status_code == 404:
                return (
                    None,
                    "",
                    f"ElevenLabs voice ID '{voice_id}' was not found. Please verify ELEVENLABS_VOICE_ID in .env.",
                )
            else:
                logger.error(
                    f"ElevenLabs API error ({response.status_code}): {err_message}"
                )
                return (
                    None,
                    "",
                    f"ElevenLabs service returned an error ({response.status_code}): {err_message}",
                )

        except requests.exceptions.Timeout:
            logger.error("ElevenLabs request timed out.")
            return None, "", "Request to ElevenLabs voice service timed out."
        except requests.exceptions.ConnectionError:
            logger.error("ElevenLabs connection error.")
            return None, "", "Failed to connect to ElevenLabs API. Check your internet connection."
        except Exception as e:
            logger.error(f"Unexpected error in ElevenLabsService: {e}")
            return None, "", f"An error occurred while generating speech: {str(e)}"


elevenlabs_service = ElevenLabsService()
