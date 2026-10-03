import os
import logging
from dotenv import load_dotenv

# Load environment variables with override enabled to allow local .env precedence
load_dotenv(override=True)

from flask import Flask, render_template, request, jsonify, Response
from services.gemini_service import gemini_service
from services.elevenlabs_service import elevenlabs_service
from services.text_cleaner import clean_text_for_tts

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False


@app.route("/")
def index():
    """Renders the futuristic JARVIS HUD voice interface."""
    return render_template("index.html")


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint to verify system and service statuses."""
    return jsonify({
        "status": "healthy",
        "gemini_configured": gemini_service.is_configured(),
        "elevenlabs_configured": elevenlabs_service.is_configured(),
        "gemini_model": gemini_service.model_name,
        "elevenlabs_voice_id": elevenlabs_service._get_voice_id(),
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Receives user speech text and conversational history.
    Calls Gemini API to generate JARVIS's natural response.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({
            "success": False,
            "error": "Invalid request. JSON payload is required."
        }), 400

    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({
            "success": False,
            "error": "Message cannot be empty."
        }), 400

    history = data.get("history", [])
    if not isinstance(history, list):
        history = []

    logger.info(f"Received message: '{user_message}' (History turns: {len(history)})")

    response_text, is_success = gemini_service.generate_response(user_message, history)

    if not is_success:
        return jsonify({
            "success": False,
            "error": response_text
        }), 502 if "Gemini" in response_text else 400

    # Build updated history
    updated_history = list(history)
    updated_history.append({"role": "user", "content": user_message})
    updated_history.append({"role": "assistant", "content": response_text})

    # Prepare sanitized spoken text (tts_text) free of Markdown or symbols
    tts_text = clean_text_for_tts(response_text)
    logger.info(f"Prepared clean TTS speech text ({len(tts_text)} chars). Preview: '{tts_text[:75]}...'")

    return jsonify({
        "success": True,
        "response": response_text,
        "tts_text": tts_text,
        "history": updated_history
    })


@app.route("/api/tts", methods=["POST"])
def tts():
    """
    Converts text response to ElevenLabs spoken voice audio.
    Cleans all Markdown and symbols so only natural spoken English is sent.
    Streams back audio/mpeg binary content.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({
            "success": False,
            "error": "Invalid request. JSON payload is required."
        }), 400

    raw_text = data.get("text", "").strip()
    if not raw_text:
        return jsonify({
            "success": False,
            "error": "Text cannot be empty for voice synthesis."
        }), 400

    # Ensure speech text is thoroughly cleaned of any Markdown syntax, symbols, or fences
    cleaned_speech_text = clean_text_for_tts(raw_text)
    if not cleaned_speech_text:
        cleaned_speech_text = raw_text

    logger.info(f"Generating ElevenLabs audio for cleaned speech ({len(cleaned_speech_text)} chars): '{cleaned_speech_text[:60]}...'")

    audio_bytes, content_type, error = elevenlabs_service.text_to_speech(cleaned_speech_text)

    if error:
        is_plan_limitation = "plan limitation" in error.lower() or "paid_plan_required" in error.lower()
        status_code = 402 if is_plan_limitation else (400 if "not configured" in error or "authentication" in error or "key notice" in error else 502)
        return jsonify({
            "success": False,
            "error": error,
            "is_plan_limitation": is_plan_limitation
        }), status_code

    return Response(
        audio_bytes,
        mimetype=content_type or "audio/mpeg",
        headers={
            "Content-Disposition": "inline; filename=jarvis_response.mp3",
            "Cache-Control": "no-cache"
        }
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    logger.info(f"Starting JARVIS Voice AI on http://localhost:{port}")
    debug = os.getenv("FLASK_DEBUG", "").lower() in ("1", "true")
    app.run(host="0.0.0.0", port=port, debug=debug)
