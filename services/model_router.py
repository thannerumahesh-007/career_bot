"""
Centralized Gemini Model Router and Quota Resilience System for CareerBot.
Routes requests across feature-specific models with automatic fallback,
catching 429 Resource Exhaustion, timeouts, and network errors gracefully.
Classifies errors and halts retry chains on authentication failures immediately.
"""

import os
import re
import time
import logging
from typing import List, Optional, Dict, Any
from config import Config

logger = logging.getLogger("CareerBot.ModelRouter")

try:
    from google import genai
    from google.genai import types
except Exception:
    genai = None
    types = None


class ErrorCategory:
    """Standardized error categories for model routing resilience."""
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    TEMPORARY_ERROR = "TEMPORARY_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


# Candidate model pools per feature with configurable env overrides
DEFAULT_FEATURE_POOLS: Dict[str, List[str]] = {
    "chat": [
        Config.GEMINI_FAST_MODEL or "gemini-3.5-flash",
        Config.GEMINI_PRIMARY_MODEL or "gemini-3.5-flash",
        Config.GEMINI_FALLBACK_MODEL or "gemini-flash-latest",
        "gemini-flash-latest",
        "gemini-3.5-flash-lite"
    ],
    "resume": [
        Config.GEMINI_RESUME_MODEL or "gemini-3.5-flash",
        Config.GEMINI_PRIMARY_MODEL or "gemini-3.5-flash",
        Config.GEMINI_FALLBACK_MODEL or "gemini-flash-latest"
    ],
    "interview": [
        Config.GEMINI_INTERVIEW_MODEL or "gemini-3.5-flash",
        Config.GEMINI_PRIMARY_MODEL or "gemini-3.5-flash",
        Config.GEMINI_FALLBACK_MODEL or "gemini-flash-latest"
    ],
    "news": [
        Config.GEMINI_LIGHT_MODEL or "gemini-flash-latest",
        Config.GEMINI_FALLBACK_MODEL or "gemini-flash-latest",
        "gemini-3.5-flash"
    ],
    "job_summary": [
        Config.GEMINI_LIGHT_MODEL or "gemini-flash-latest",
        Config.GEMINI_FALLBACK_MODEL or "gemini-flash-latest",
        "gemini-3.5-flash"
    ]
}

TASK_MODEL_POOLS = DEFAULT_FEATURE_POOLS


class ModelRouter:
    """Centralized router managing Gemini model selection, error classification, and graceful fallback."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or Config.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.client = None
        self.last_status: Dict[str, Any] = {
            "provider": "gemini",
            "status": "initialized",
            "error_type": None,
            "fallback": None,
            "model": None
        }
        self._init_client()

    def _init_client(self):
        """Initializes Google GenAI client safely."""
        if not self.api_key:
            self.api_key = Config.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

        if self.api_key and genai:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize GenAI client: {self._sanitize_error(str(e))}")
                self.client = None

    def _mask_key(self, key: Optional[str]) -> str:
        """Masks an API key for safe structured logging."""
        if not key:
            return "None"
        if len(key) <= 8:
            return "****"
        return f"{key[:4]}...{key[-4:]}"

    def get_key_info(self) -> Dict[str, Any]:
        """Returns safe summary information about the loaded key without exposing it."""
        return {
            "loaded": bool(self.api_key),
            "source": "environment variable",
            "length": len(self.api_key) if self.api_key else 0
        }

    def is_available(self) -> bool:
        """Returns True if client is configured and available."""
        if not self.client:
            self._init_client()
        return self.client is not None and bool(self.api_key)

    def classify_error(self, exc: Exception) -> str:
        """
        Classifies exceptions into standard error categories:
        AUTHENTICATION_ERROR, RATE_LIMIT_ERROR, MODEL_NOT_FOUND,
        TEMPORARY_ERROR, NETWORK_ERROR, UNKNOWN_ERROR.
        """
        err_str = str(exc)
        err_lower = err_str.lower()

        # 1. Authentication / Invalid API key
        if (
            "api key not valid" in err_lower
            or "api_key_invalid" in err_lower
            or "invalid api key" in err_lower
            or "api key expired" in err_lower
            or "permission_denied" in err_lower
            or "401" in err_str
            or ("400" in err_str and ("api key" in err_lower or "api_key" in err_lower or "invalid_argument" in err_lower and "key" in err_lower))
        ):
            return ErrorCategory.AUTHENTICATION_ERROR

        # 2. Rate Limit / Quota Exceeded (429)
        if "429" in err_str or "resource_exhausted" in err_lower or "quota" in err_lower:
            return ErrorCategory.RATE_LIMIT_ERROR

        # 3. Model Not Found / Deprecated (404)
        if (
            "404" in err_str
            or "not_found" in err_lower
            or "is not found" in err_lower
            or "no longer available" in err_lower
            or "model not found" in err_lower
        ):
            return ErrorCategory.MODEL_NOT_FOUND

        # 4. Temporary Service / Overload / 503 / 500 / Timeout
        if (
            "503" in err_str
            or "unavailable" in err_lower
            or "500" in err_str
            or "502" in err_str
            or "504" in err_str
            or "timeout" in err_lower
            or "deadline_exceeded" in err_lower
            or "overloaded" in err_lower
        ):
            return ErrorCategory.TEMPORARY_ERROR

        # 5. Network / Socket / SSL
        if (
            "connection" in err_lower
            or "dns" in err_lower
            or "network" in err_lower
            or "socket" in err_lower
            or "ssl" in err_lower
        ):
            return ErrorCategory.NETWORK_ERROR

        return ErrorCategory.UNKNOWN_ERROR

    def get_candidate_models(self, feature: str) -> List[str]:
        """Returns ordered list of candidate models for a given feature."""
        pool = DEFAULT_FEATURE_POOLS.get(feature, DEFAULT_FEATURE_POOLS["chat"])
        # Deduplicate while preserving order
        seen = set()
        candidates = []
        for m in pool:
            if m and m not in seen:
                seen.add(m)
                candidates.append(m)
        return candidates

    def generate_content(
        self,
        task: Optional[str] = None,
        feature: Optional[str] = None,
        prompt: Optional[str] = None,
        contents: Optional[Any] = None,
        config: Any = None,
        system_instruction: Optional[str] = None,
        max_tokens: Optional[int] = None
    ) -> Optional[str]:
        """
        Executes generation on the primary model for the given feature,
        falling back automatically through candidate models upon transient failure.
        Immediately stops and aborts retry chain on AUTHENTICATION_ERROR.
        """
        feature_key = task or feature or "chat"
        prompt_text = prompt if prompt is not None else contents
        start_time = time.time()

        if not self.is_available():
            duration = round(time.time() - start_time, 3)
            logger.info(
                f"Feature: {feature_key} | Provider: local_fallback | Selected model: none | "
                f"Error category: {ErrorCategory.AUTHENTICATION_ERROR} | Fallback: local | Duration: {duration}s"
            )
            self.last_status = {
                "provider": "local_fallback",
                "status": "failed",
                "error_type": "authentication_error",
                "fallback": "local",
                "model": None
            }
            return None

        candidates = self.get_candidate_models(feature_key)
        primary_model = candidates[0] if candidates else "unknown"
        last_error_cat = ErrorCategory.UNKNOWN_ERROR

        for idx, model_name in enumerate(candidates):
            model_start = time.time()
            try:
                kwargs = {
                    "model": model_name,
                    "contents": prompt_text
                }

                # Setup configuration if system instruction or max tokens passed
                if system_instruction or max_tokens:
                    cfg_kwargs = {}
                    if system_instruction:
                        cfg_kwargs["system_instruction"] = system_instruction
                    if max_tokens:
                        cfg_kwargs["max_output_tokens"] = max_tokens
                    if types and hasattr(types, "GenerateContentConfig"):
                        kwargs["config"] = types.GenerateContentConfig(**cfg_kwargs)
                    elif config is not None:
                        kwargs["config"] = config
                elif config is not None:
                    kwargs["config"] = config

                response = self.client.models.generate_content(**kwargs)
                if response and response.text and response.text.strip():
                    total_duration = round(time.time() - start_time, 3)
                    fallback_used = model_name if idx > 0 else "none"
                    logger.info(
                        f"Feature: {feature_key} | Provider: gemini | Selected model: {model_name} | "
                        f"Fallback: {fallback_used} | Duration: {total_duration}s"
                    )
                    self.last_status = {
                        "provider": "gemini",
                        "status": "success",
                        "error_type": None,
                        "fallback": None if idx == 0 else model_name,
                        "model": model_name
                    }
                    return response.text.strip()

            except Exception as exc:
                elapsed = round(time.time() - model_start, 3)
                error_cat = self.classify_error(exc)
                last_error_cat = error_cat
                reason = self._sanitize_error(str(exc))

                # On AUTHENTICATION_ERROR: STOP immediately! Do not retry with the same invalid key.
                if error_cat == ErrorCategory.AUTHENTICATION_ERROR:
                    logger.error(
                        f"Feature: {feature_key} | Provider: gemini | Selected model: {model_name} | "
                        f"Error category: {error_cat} | Reason: {reason} | Fallback: local_fallback | Duration: {elapsed}s"
                    )
                    self.last_status = {
                        "provider": "local_fallback",
                        "status": "failed",
                        "error_type": "authentication_error",
                        "fallback": "local",
                        "model": model_name
                    }
                    return None

                # For quota, model_not_found, temporary, network: fall back to next model
                next_model = candidates[idx + 1] if idx + 1 < len(candidates) else "local_fallback"
                logger.warning(
                    f"Feature: {feature_key} | Provider: gemini | Selected model: {model_name} | "
                    f"Error category: {error_cat} | Reason: {reason} | Fallback: {next_model} | Duration: {elapsed}s"
                )
                continue

        total_duration = round(time.time() - start_time, 3)
        logger.info(
            f"Feature: {feature_key} | Provider: local_fallback | Selected model: {primary_model} | "
            f"Error category: {last_error_cat} | Fallback: local_fallback | Reason: all models exhausted | Duration: {total_duration}s"
        )
        self.last_status = {
            "provider": "local_fallback",
            "status": "failed",
            "error_type": last_error_cat.lower(),
            "fallback": "local",
            "model": primary_model
        }
        return None

    def test_connection(self) -> Dict[str, Any]:
        """
        Safely tests Gemini connection and API key validity without exposing credentials.
        Returns diagnostic status dictionary.
        """
        if not self.api_key:
            return {
                "success": False,
                "api_key_loaded": False,
                "key_source": "environment variable",
                "key_length": 0,
                "client_initialized": False,
                "model_accessible": False,
                "model": None,
                "error_category": ErrorCategory.AUTHENTICATION_ERROR,
                "message": "Gemini authentication/configuration failed: No API key found."
            }

        if not self.client:
            self._init_client()

        if not self.client:
            return {
                "success": False,
                "api_key_loaded": True,
                "key_source": "environment variable",
                "key_length": len(self.api_key),
                "client_initialized": False,
                "model_accessible": False,
                "model": None,
                "error_category": ErrorCategory.AUTHENTICATION_ERROR,
                "message": "Gemini authentication/configuration failed: Client initialization failed."
            }

        test_model = Config.GEMINI_PRIMARY_MODEL or "gemini-3.5-flash"
        try:
            res = self.client.models.generate_content(
                model=test_model,
                contents="ping"
            )
            if res and res.text:
                return {
                    "success": True,
                    "api_key_loaded": True,
                    "key_source": "environment variable",
                    "key_length": len(self.api_key),
                    "client_initialized": True,
                    "model_accessible": True,
                    "model": test_model,
                    "error_category": None,
                    "message": "Gemini authentication and generation succeeded."
                }
        except Exception as exc:
            error_cat = self.classify_error(exc)
            return {
                "success": False,
                "api_key_loaded": True,
                "key_source": "environment variable",
                "key_length": len(self.api_key),
                "client_initialized": True,
                "model_accessible": False,
                "model": test_model,
                "error_category": error_cat,
                "message": f"Gemini authentication/configuration failed: {error_cat}"
            }

        return {
            "success": False,
            "api_key_loaded": True,
            "key_source": "environment variable",
            "key_length": len(self.api_key),
            "client_initialized": True,
            "model_accessible": False,
            "model": test_model,
            "error_category": ErrorCategory.UNKNOWN_ERROR,
            "message": "Gemini authentication/configuration failed: Empty response."
        }

    def _sanitize_error(self, error_msg: str) -> str:
        """Removes any accidental API key or sensitive data from error message."""
        if not error_msg:
            return "Unknown error"
        sanitized = error_msg
        if self.api_key and len(self.api_key) > 5:
            sanitized = sanitized.replace(self.api_key, "[REDACTED_API_KEY]")
        sanitized = re.sub(r"AIza[0-9A-Za-z-_]{35}", "[REDACTED_API_KEY]", sanitized)
        sanitized = re.sub(r"AQ[0-9A-Za-z-_]{35,}", "[REDACTED_API_KEY]", sanitized)
        if "429" in sanitized or "RESOURCE_EXHAUSTED" in sanitized:
            return "429 RESOURCE_EXHAUSTED / Quota exceeded"
        if "404" in sanitized or "NOT_FOUND" in sanitized:
            return "404 NOT_FOUND / Model unavailable"
        if "503" in sanitized or "UNAVAILABLE" in sanitized:
            return "503 Service Temporarily Unavailable"
        if "timeout" in sanitized.lower():
            return "Request Timeout"
        if "API key not valid" in sanitized:
            return "400 INVALID_ARGUMENT: API key not valid"
        return sanitized[:180]


# Global singleton instance
model_router = ModelRouter()
