# JARVIS Voice AI ⚡

A standalone, voice-first personal AI assistant built with **Google Gemini** as the conversational intelligence brain, **ElevenLabs** for ultra-realistic voice synthesis, and a futuristic **Iron Man HUD** arc reactor interface.

---

## 🌟 Key Features

* **Natural Voice Conversation**: Speak naturally to JARVIS using browser microphone speech recognition, receive contextual responses from Gemini, and hear them spoken aloud via ElevenLabs.
* **Contextual Memory**: Full multi-turn conversation memory within the session. JARVIS naturally understands follow-ups (e.g., *"What do you suggest?"* after discussing what to do).
* **Futuristic Arc Reactor HUD**:
  * Pure Iron Man HUD aesthetic: deep cyber void background with vibrant Arc Reactor Cyan (`#00f0ff`) glow. Strictly no purple theme.
  * Interactive HTML5 Canvas particle system orbiting a central pulsating core.
  * Real-time audio waveform and frequency reactivity.
  * 4 distinct animated states:
    * **IDLE**: Gentle slow orbital rotation; JARVIS awaits instructions.
    * **LISTENING**: Center core pulses rhythmically, particles expand and glow green.
    * **THINKING**: High-speed particle vortex acceleration while Gemini computes.
    * **SPEAKING**: Real-time frequency pulsing synchronized with ElevenLabs audio playback.
    * **PAUSED**: Suspended amber glow and calm particle suspension; resumes seamlessly from the exact paused second.
* **Instant Pause & Resume Controls**: Pause ongoing speech playback immediately without regenerating or truncating the response, and resume seamlessly from the exact position.
* **Indian Standard Time (IST)**: Real-time HUD telemetry clock synchronized with `Asia/Kolkata`.
* **Dual Input Mode**: Voice speech recognition + HUD terminal text input bar for quiet environments.
* **Clean & Modular Architecture**: Gemini logic and ElevenLabs logic are encapsulated in standalone services, ready to be embedded into CareerBot or other applications.

---

## 📁 Project Structure

```text
jarvis/
│
├── app.py                     # Flask server with API endpoints
├── .env                       # Local environment variables (API keys)
├── .env.example               # Template environment configuration
├── .gitignore                 # Excludes .env, virtualenvs, cache
├── requirements.txt           # Project dependencies
├── README.md                  # Documentation and setup guide
│
├── services/
│   ├── gemini_service.py      # Google Gemini 2.5 API integration & context
│   └── elevenlabs_service.py  # ElevenLabs Text-to-Speech API integration
│
├── templates/
│   └── index.html             # Futuristic Iron Man HUD interface
│
└── static/
    ├── css/
    │   └── style.css          # HUD styling, cyan glow, typography, responsive
    └── js/
        └── app.js             # Canvas particle physics, Web Speech API, audio reactivity
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites

* Python 3.10+ (Tested on Python 3.14)
* A Google Gemini API key ([Google AI Studio](https://aistudio.google.com/))
* An ElevenLabs API key ([ElevenLabs](https://elevenlabs.io/))

### 2. Install Dependencies

Clone or navigate to the project directory:

```bash
cd jarvis
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Open `.env` (or copy from `.env.example`) and add your API keys:

```env
# Google Gemini API Key
GEMINI_API_KEY=your_actual_gemini_key_here
GEMINI_MODEL=gemini-2.5-flash

# ElevenLabs Configuration
ELEVENLABS_API_KEY=your_actual_elevenlabs_key_here
# Configured JARVIS voice: wWWn96OtTHu1sn8SRGEr
ELEVENLABS_VOICE_ID=wWWn96OtTHu1sn8SRGEr
ELEVENLABS_MODEL_ID=eleven_turbo_v2_5

# Server Port
PORT=5000
```

### 4. Run the Application

```bash
python app.py
```

Open your browser and navigate to:
**[http://localhost:5000](http://localhost:5000)**

---

## 🎙️ How to Use

1. Click the **Microphone Button** or click directly on the **Central Arc Reactor Core**.
2. Allow browser microphone access when prompted.
3. Speak your prompt or question naturally (e.g., *"Hello JARVIS, who are you?"* or *"I'm feeling bored today"*).
4. Watch the state transition:
   * **LISTENING** ➔ **THINKING** ➔ **SPEAKING**
5. Ask follow-up questions (e.g., *"What do you suggest?"*). JARVIS retains context across all turns.
6. Click **RESET** in the terminal header anytime to clear the conversation memory.

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Renders the JARVIS HUD web interface |
| `GET` | `/api/health` | Returns service health status and API configuration flags |
| `POST` | `/api/chat` | Accepts `{ "message": str, "history": list }` and returns `{ "response": str, "history": list }` |
| `POST` | `/api/tts` | Accepts `{ "text": str }` and streams back binary `audio/mpeg` |

---

## 🛡️ Error Handling & Resiliency

* **Missing / Invalid Gemini API Key**: The server returns a clear message prompting the user to update their key in `.env`.
* **Missing / Invalid ElevenLabs API Key**: The frontend displays a warning badge and automatically switches to browser neural speech synthesis so audio playback continues uninterrupted.
* **Microphone Permissions Denied**: The interface shows a HUD notification and allows seamless text input through the terminal bar.
* **Network & Quota Limits**: Cleanly caught and surfaced as user-friendly messages rather than unhandled server crashes.

---

## 🔗 CareerBot Integration Readiness

The backend services are designed for effortless modular integration:
* `services/gemini_service.py` receives a standard message and history list `[{"role": "user"|"assistant", "content": "..."}]`, making it compatible with any external conversation store.
* `services/elevenlabs_service.py` operates completely decoupled from session state, converting raw strings to audio streams.
* The frontend HUD can be embedded as a modal, full-screen overlay, or iframe inside CareerBot.
