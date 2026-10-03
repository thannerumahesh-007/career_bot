import os
import logging
from dotenv import load_dotenv
from typing import List, Dict, Any, Tuple
from google import genai
from google.genai import types
from google.genai.errors import APIError, ClientError

logger = logging.getLogger(__name__)

JARVIS_SYSTEM_INSTRUCTION = (
    "You are JARVIS, a capable general-purpose conversational AI assistant. "
    "Understand the user's exact request before answering. "
    "Answer the question directly and completely. "
    "Follow the requested level of detail. "
    "Maintain conversational context across turns. "
    "Do not give generic or unrelated answers. "
    "If the user asks for an explanation, provide the explanation rather than merely naming a topic. "
    "Formatting rules for natural speech: "
    "1. Speak naturally using full sentences and clear paragraphs. "
    "2. Do NOT use Markdown formatting such as headings (#, ##, ###), bold stars (**), italics (*), bullet characters (- or *), numbered Markdown lists, or tables. "
    "3. Structure explanations conversationally using spoken transition words (such as 'First,', 'Second,', 'Additionally,', 'In conclusion,'). "
    "4. Do not artificially truncate responses; if the user asks for a detailed explanation, provide a thorough, informative, and complete answer."
)


class GeminiService:
    @property
    def model_name(self) -> str:
        load_dotenv(override=True)
        return os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    def _get_api_key(self) -> str:
        load_dotenv(override=True)
        # Prioritize GEMINI_API_KEY from .env, then GOOGLE_API_KEY
        return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""

    def is_configured(self) -> bool:
        key = self._get_api_key()
        return bool(key and key.strip() and key != "your_gemini_api_key_here")

    def _get_client(self) -> genai.Client:
        key = self._get_api_key()
        if not key or key == "your_gemini_api_key_here":
            raise ValueError(
                "Gemini API key is not configured. Please set GEMINI_API_KEY in your .env file."
            )
        # Prevent collision with invalid system-wide GOOGLE_API_KEY
        if "GOOGLE_API_KEY" in os.environ:
            os.environ.pop("GOOGLE_API_KEY", None)
        return genai.Client(api_key=key)

    def generate_response(
        self, user_message: str, history: List[Dict[str, str]] = None
    ) -> Tuple[str, bool]:
        """
        Generates a natural conversational response using Gemini.
        Returns: (response_text, success_boolean)
        """
        if not user_message or not user_message.strip():
            return "I didn't catch that, sir. Could you please speak again?", False

        if not self.is_configured():
            return (
                "Gemini API key is missing. Please configure GEMINI_API_KEY in your .env file.",
                False,
            )

        client = None
        try:
            client = self._get_client()
            
            # Format history for Gemini API
            # Standard history list: [{"role": "user"|"assistant", "content": "..."}]
            contents = []
            if history:
                for entry in history:
                    role = entry.get("role", "")
                    content = entry.get("content", "")
                    if not content:
                        continue
                    # In Gemini API, roles are 'user' and 'model'
                    gemini_role = "model" if role in ("assistant", "model") else "user"
                    contents.append(
                        types.Content(
                            role=gemini_role,
                            parts=[types.Part.from_text(text=content)],
                        )
                    )

            # Append current user message
            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=user_message.strip())],
                )
            )

            config = types.GenerateContentConfig(
                system_instruction=JARVIS_SYSTEM_INSTRUCTION,
                temperature=0.7,
                max_output_tokens=2048,
            )

            # Try requested model, and fallback gracefully if 404 or not found
            models_to_try = [
                self.model_name,
                "gemini-3.5-flash",
                "gemini-3.1-flash-lite",
                "gemini-3.8-flash",
            ]
            # Deduplicate while preserving order
            seen = set()
            models_to_try = [m for m in models_to_try if not (m in seen or seen.add(m))]

            response = None
            last_err = None
            for model_candidate in models_to_try:
                try:
                    response = client.models.generate_content(
                        model=model_candidate,
                        contents=contents,
                        config=config,
                    )
                    if response and response.text:
                        break
                except ClientError as ce:
                    last_err = ce
                    if "NOT_FOUND" in str(ce) or "404" in str(ce):
                        logger.warning(f"Model {model_candidate} not available (404), trying fallback...")
                        continue
                    if "RESOURCE_EXHAUSTED" in str(ce) or "429" in str(ce):
                        logger.warning(f"Model {model_candidate} rate limited (429), trying fallback...")
                        continue
                    raise ce
                except Exception as ex:
                    last_err = ex
                    if "503" in str(ex) or "UNAVAILABLE" in str(ex) or "RESOURCE_EXHAUSTED" in str(ex) or "429" in str(ex):
                        logger.warning(f"Model {model_candidate} temporarily unavailable, trying fallback...")
                        continue
                    raise ex

            if response and response.text:
                return response.text.strip(), True
            elif last_err:
                raise last_err
            else:
                return (
                    "I processed your query, but received an empty response. How else may I assist you?",
                    True,
                )

        except ClientError as e:
            error_msg = str(e)
            logger.error(f"Gemini ClientError: {error_msg}")
            if "API_KEY_INVALID" in error_msg or "API key not valid" in error_msg:
                return (
                    "Your Gemini API key appears to be invalid. Please verify your GEMINI_API_KEY in .env.",
                    False,
                )
            elif "RESOURCE_EXHAUSTED" in error_msg or "quota" in error_msg.lower():
                return (
                    "Gemini API rate limit or quota exceeded. Please try again in a moment.",
                    False,
                )
            return f"Gemini encountered an issue: {error_msg.splitlines()[0]}", False

        except APIError as e:
            logger.error(f"Gemini APIError: {e}")
            return "A service error occurred while communicating with Gemini. Please try again.", False

        except Exception as e:
            logger.error(f"Unexpected error in GeminiService: {e}")
            return f"An unexpected error occurred: {str(e)}", False


gemini_service = GeminiService()
