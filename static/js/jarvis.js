/**
 * JARVIS VOICE AI - CLIENT ENGINE FOR CAREERBOT
 * Fully integrated Live Voice Interface.
 * Handles:
 * - HTML5 Canvas Particle Orbit & Core Visualizer (IDLE, LISTENING, THINKING, SPEAKING, PAUSED)
 * - Web Speech API Speech Recognition
 * - CareerBot Shared Conversation Backend (/api/chat)
 * - ElevenLabs Text-to-Speech Audio Stream & Web Audio Analyser (/api/tts)
 * - Live HUD Controls: Pause / Resume, Exit Live Mode, Telemetry & IST Clock
 */

function getJarvisCsrfToken() {
    return document.querySelector('input[name="csrf_token"]')?.value ||
           document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') ||
           window.csrfToken || '';
}

class JarvisHUD {
    constructor() {
        this.overlay = document.getElementById('jarvis-live-overlay');
        if (!this.overlay) return;

        // UI Elements
        this.canvas = document.getElementById('jarvis-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.micBtn = document.getElementById('jarvis-mic-btn');
        this.micCaption = document.getElementById('jarvis-mic-caption');
        this.stateDisplay = document.getElementById('state-display');
        this.stateSubText = document.getElementById('state-sub-text');
        this.coreStateBadge = document.getElementById('core-state-badge');
        this.coreFrequencyReadout = document.getElementById('core-frequency-readout');
        this.transcriptFeed = document.getElementById('transcript-feed');
        this.textForm = document.getElementById('text-fallback-form');
        this.textInput = document.getElementById('jarvis-text-input');
        this.clearHistoryBtn = document.getElementById('clear-history-btn');
        this.toggleTranscriptBtn = document.getElementById('toggle-transcript-btn');
        this.exitLiveBtn = document.getElementById('exit-live-btn');
        this.audioPlayer = document.getElementById('tts-audio-player');
        this.toast = document.getElementById('hud-toast');
        this.toastMessage = document.getElementById('toast-message');
        this.statusDot = document.getElementById('system-status-dot');
        this.statusText = document.getElementById('system-status-text');
        this.waveformContainer = document.getElementById('waveform-container');
        this.waveformBars = Array.from(document.querySelectorAll('.waveform-bar'));
        this.sysClock = document.getElementById('sys-clock');

        // Pause / Resume Control Elements
        this.pauseBtn = document.getElementById('jarvis-pause-btn');
        this.pauseIcon = document.getElementById('pause-icon');
        this.playIcon = document.getElementById('play-icon');
        this.pauseBtnLabel = document.getElementById('pause-btn-label');

        // Language Selection
        this.langSelect = document.getElementById('jarvisLangSelect');
        this.selectedLanguage = localStorage.getItem('careerbot_language') || 'en-IN';
        if (this.langSelect) {
            this.langSelect.value = this.selectedLanguage;
        }
        window.jarvisHUDInstance = this;

        // State machine: 'IDLE' | 'LISTENING' | 'THINKING' | 'SPEAKING' | 'PAUSED'
        this.state = 'IDLE';
        this.recognition = null;
        this.isRecognitionActive = false;
        this.isOpen = false;
        this.currentUtterance = null;

        // Web Audio API for Live Voice Reactivity
        this.audioCtx = null;
        this.analyser = null;
        this.audioSource = null;
        this.dataArray = null;

        // Particle System Properties
        this.particles = [];
        this.numParticles = 48;
        this.center = { x: 300, y: 300 };
        this.rotationAngle = 0;
        this.pulsePhase = 0;
        this.animFrameId = null;

        this.init();
    }

    async init() {
        this.resizeCanvas();
        window.addEventListener('resize', () => {
            if (this.isOpen) this.resizeCanvas();
        });

        this.initParticles();
        this.initClock();
        this.initSpeechRecognition();
        this.bindEvents();
        this.checkSystemHealth();
    }

    /* ==========================================================================
       CANVAS & PARTICLE SYSTEM
       ========================================================================== */
    resizeCanvas() {
        if (!this.canvas) return;
        const rect = this.canvas.parentElement.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        const width = rect.width || 420;
        const height = rect.height || 420;
        this.canvas.width = width * dpr;
        this.canvas.height = height * dpr;
        this.ctx.scale(dpr, dpr);
        this.center = { x: width / 2, y: height / 2 };
    }

    initParticles() {
        this.particles = [];
        const baseRadius = 85;

        for (let i = 0; i < this.numParticles; i++) {
            const ring = i % 4;
            const orbitalRadius = baseRadius + ring * 28 + (Math.random() * 12 - 6);
            const speed = (0.003 + (ring * 0.002)) * (i % 2 === 0 ? 1 : -0.85);

            this.particles.push({
                angle: (Math.PI * 2 / this.numParticles) * i + Math.random() * 0.5,
                radius: orbitalRadius,
                baseRadius: orbitalRadius,
                speed: speed,
                baseSpeed: speed,
                size: Math.random() * 2.2 + 1.2,
                opacity: Math.random() * 0.6 + 0.4,
                wobble: Math.random() * Math.PI * 2,
                wobbleSpeed: Math.random() * 0.05 + 0.02,
                ringIndex: ring
            });
        }
    }

    setState(newState, subText = '') {
        this.state = newState;
        if (this.stateDisplay) this.stateDisplay.textContent = newState;
        if (this.coreStateBadge) this.coreStateBadge.textContent = newState;

        if (this.stateSubText) {
            if (subText) {
                this.stateSubText.textContent = subText;
            } else {
                switch (newState) {
                    case 'IDLE':
                        this.stateSubText.textContent = 'STANDBY // READY FOR VOICE INPUT';
                        break;
                    case 'LISTENING':
                        this.stateSubText.textContent = 'RECEIVING AUDIO STREAM...';
                        break;
                    case 'THINKING':
                        this.stateSubText.textContent = 'NEURAL PROCESSING...';
                        break;
                    case 'SPEAKING':
                        this.stateSubText.textContent = 'ELEVENLABS VOICE TRANSMISSION';
                        break;
                    case 'PAUSED':
                        this.stateSubText.textContent = 'AUDIO SUSPENDED // CLICK RESUME';
                        break;
                }
            }
        }

        // State styles for Core Readout & State Display
        if (this.coreStateBadge) {
            if (newState === 'PAUSED') {
                this.coreStateBadge.classList.add('state-paused');
                if (this.stateDisplay) this.stateDisplay.classList.add('state-paused');
            } else {
                this.coreStateBadge.classList.remove('state-paused');
                if (this.stateDisplay) this.stateDisplay.classList.remove('state-paused');
            }
        }

        // Update mic button active styling
        if (this.micBtn) {
            if (newState === 'LISTENING') {
                this.micBtn.classList.add('listening');
                if (this.micCaption) this.micCaption.textContent = 'LISTENING... SPEAK NOW';
            } else {
                this.micBtn.classList.remove('listening');
                if (this.micCaption) {
                    this.micCaption.textContent = newState === 'SPEAKING' ? 'JARVIS SPEAKING' : (newState === 'PAUSED' ? 'SPEECH PAUSED' : 'CLICK TO ACTIVATE VOICE');
                }
            }
        }

        // Update pause button state
        if (this.pauseBtn) {
            if (newState === 'SPEAKING') {
                this.pauseBtn.disabled = false;
                this.pauseBtn.classList.add('speaking');
                this.pauseBtn.classList.remove('is-paused');
                if (this.pauseBtnLabel) this.pauseBtnLabel.textContent = 'PAUSE';
                if (this.pauseIcon) this.pauseIcon.style.display = 'block';
                if (this.playIcon) this.playIcon.style.display = 'none';
            } else if (newState === 'PAUSED') {
                this.pauseBtn.disabled = false;
                this.pauseBtn.classList.remove('speaking');
                this.pauseBtn.classList.add('is-paused');
                if (this.pauseBtnLabel) this.pauseBtnLabel.textContent = 'RESUME';
                if (this.pauseIcon) this.pauseIcon.style.display = 'none';
                if (this.playIcon) this.playIcon.style.display = 'block';
            } else {
                this.pauseBtn.disabled = true;
                this.pauseBtn.classList.remove('speaking', 'is-paused');
                if (this.pauseBtnLabel) this.pauseBtnLabel.textContent = 'PAUSE';
                if (this.pauseIcon) this.pauseIcon.style.display = 'block';
                if (this.playIcon) this.playIcon.style.display = 'none';
            }
        }

        // Waveform activity
        if (this.waveformContainer) {
            if (newState === 'SPEAKING' || newState === 'LISTENING') {
                this.waveformContainer.classList.add('active');
            } else {
                this.waveformContainer.classList.remove('active');
            }
        }
    }

    render(time) {
        if (!this.isOpen) return;

        const ctx = this.ctx;
        const width = this.canvas.width / (window.devicePixelRatio || 1);
        const height = this.canvas.height / (window.devicePixelRatio || 1);
        const cx = this.center.x;
        const cy = this.center.y;

        ctx.clearRect(0, 0, width, height);

        // Calculate audio reactivity
        let audioReact = 0;
        if (this.analyser && this.dataArray && this.state === 'SPEAKING') {
            this.analyser.getByteFrequencyData(this.dataArray);
            let sum = 0;
            for (let i = 0; i < this.dataArray.length; i++) {
                sum += this.dataArray[i];
            }
            audioReact = (sum / this.dataArray.length) / 255;
        } else if (this.state === 'LISTENING') {
            audioReact = 0.35 + Math.sin(time * 0.008) * 0.2;
        } else if (this.state === 'THINKING') {
            audioReact = 0.5 + Math.sin(time * 0.02) * 0.3;
        }

        this.drawParticles(ctx, cx, cy, audioReact, time);
        this.drawHudArcs(ctx, cx, cy, time);
        this.updateWaveformBars(audioReact);

        this.animFrameId = requestAnimationFrame((t) => this.render(t));
    }

    drawParticles(ctx, cx, cy, audioReact, time) {
        ctx.save();

        let speedMultiplier = 1.0;
        let radiusOffset = 0;

        if (this.state === 'IDLE') {
            speedMultiplier = 0.6;
        } else if (this.state === 'LISTENING') {
            speedMultiplier = 1.4;
            radiusOffset = 10 + audioReact * 18;
        } else if (this.state === 'THINKING') {
            speedMultiplier = 3.5;
            radiusOffset = Math.sin(time * 0.005) * 15;
        } else if (this.state === 'SPEAKING') {
            speedMultiplier = 1.8 + audioReact * 1.5;
            radiusOffset = audioReact * 30;
        } else if (this.state === 'PAUSED') {
            speedMultiplier = 0.08;
            radiusOffset = 0;
        }

        for (let i = 0; i < this.particles.length; i++) {
            const p = this.particles[i];

            p.angle += p.baseSpeed * speedMultiplier;
            p.wobble += p.wobbleSpeed * (this.state === 'PAUSED' ? 0.1 : 1.0);

            const currentRadius = p.baseRadius + radiusOffset + Math.sin(p.wobble) * 6;
            const px = cx + Math.cos(p.angle) * currentRadius;
            const py = cy + Math.sin(p.angle) * currentRadius;

            // Draw connecting energy lines
            const nextP = this.particles[(i + 1) % this.particles.length];
            if (nextP.ringIndex === p.ringIndex) {
                const nextRadius = nextP.baseRadius + radiusOffset + Math.sin(nextP.wobble) * 6;
                const nx = cx + Math.cos(nextP.angle) * nextRadius;
                const ny = cy + Math.sin(nextP.angle) * nextRadius;
                const dist = Math.hypot(nx - px, ny - py);

                if (dist < 70) {
                    ctx.beginPath();
                    ctx.moveTo(px, py);
                    ctx.lineTo(nx, ny);
                    const lineColor = this.state === 'PAUSED' ? `rgba(245, 158, 11, ${(1 - dist / 70) * 0.25})` : `rgba(59, 130, 246, ${(1 - dist / 70) * 0.3})`;
                    ctx.strokeStyle = lineColor;
                    ctx.lineWidth = 0.8;
                    ctx.stroke();
                }
            }

            // Draw particle dot
            ctx.beginPath();
            const pSize = p.size * (1 + (audioReact * 0.8));
            ctx.arc(px, py, pSize, 0, Math.PI * 2);

            let particleColor = 'rgba(59, 130, 246, ';
            if (this.state === 'LISTENING') {
                particleColor = 'rgba(16, 185, 129, ';
            } else if (this.state === 'THINKING') {
                particleColor = 'rgba(96, 165, 250, ';
            } else if (this.state === 'PAUSED') {
                particleColor = 'rgba(245, 158, 11, ';
            }

            ctx.fillStyle = `${particleColor}${p.opacity})`;
            ctx.shadowColor = this.state === 'PAUSED' ? '#F59E0B' : (this.state === 'LISTENING' ? '#10B981' : '#3B82F6');
            ctx.shadowBlur = pSize * 4;
            ctx.fill();
        }

        ctx.restore();
    }

    drawHudArcs(ctx, cx, cy, time) {
        ctx.save();

        const thinkingSpeed = this.state === 'THINKING' ? 0.06 : (this.state === 'PAUSED' ? 0.0005 : 0.005);
        const angleOffset = time * thinkingSpeed;

        // Rotating Segmented Inner Ring
        ctx.beginPath();
        ctx.arc(cx, cy, 64, angleOffset, angleOffset + Math.PI * 0.8);
        ctx.strokeStyle = this.state === 'PAUSED' ? 'rgba(245, 158, 11, 0.4)' : 'rgba(59, 130, 246, 0.4)';
        ctx.lineWidth = 1.5;
        ctx.stroke();

        ctx.beginPath();
        ctx.arc(cx, cy, 64, angleOffset + Math.PI, angleOffset + Math.PI * 1.8);
        ctx.strokeStyle = this.state === 'PAUSED' ? 'rgba(245, 158, 11, 0.4)' : 'rgba(59, 130, 246, 0.4)';
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Outer Notched Compass Arcs
        const outerAngle = -time * 0.003;
        ctx.beginPath();
        ctx.arc(cx, cy, 195, outerAngle, outerAngle + Math.PI * 0.35);
        ctx.strokeStyle = 'rgba(59, 130, 246, 0.25)';
        ctx.lineWidth = 2;
        ctx.stroke();

        ctx.beginPath();
        ctx.arc(cx, cy, 195, outerAngle + Math.PI, outerAngle + Math.PI * 1.35);
        ctx.strokeStyle = 'rgba(59, 130, 246, 0.25)';
        ctx.lineWidth = 2;
        ctx.stroke();

        ctx.restore();
    }

    updateWaveformBars(reactivity) {
        this.waveformBars.forEach((bar, index) => {
            const factor = Math.sin(Date.now() * 0.015 + index * 0.5);
            let h = 4;
            if (this.state === 'SPEAKING' || this.state === 'LISTENING') {
                h = 4 + (reactivity * 18 * Math.abs(factor));
            }
            bar.style.height = `${Math.max(4, h)}px`;
        });
    }

    /* ==========================================================================
       SPEECH RECOGNITION (BROWSER)
       ========================================================================== */
    initSpeechRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

        if (!SpeechRecognition) {
            console.warn('Web Speech API is not supported in this browser.');
            if (this.statusDot) {
                this.statusDot.className = 'status-dot warn';
                this.statusText.textContent = 'MIC UNSUPPORTED';
            }
            return;
        }

        this.recognition = new SpeechRecognition();
        this.recognition.continuous = false;
        this.recognition.interimResults = false;
        this.recognition.lang = this.selectedLanguage || 'en-IN';

        this.recognition.onstart = () => {
            this.isRecognitionActive = true;
            this.setState('LISTENING');
        };

        this.recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            console.log('JARVIS recognized speech:', transcript);
            if (transcript && transcript.trim()) {
                this.handleUserMessage(transcript.trim());
            }
        };

        this.recognition.onerror = (event) => {
            console.warn('Speech recognition error:', event.error);
            this.isRecognitionActive = false;

            if (event.error === 'not-allowed' || event.error === 'permission-denied') {
                this.showToast('Microphone access denied. Please allow microphone access in browser settings.', true);
                this.setState('IDLE', 'MIC ACCESS DENIED');
            } else if (event.error === 'language-not-supported') {
                this.showToast(`Speech recognition for ${this.selectedLanguage} is not supported by this browser. You can continue using typed input.`, true);
                this.setState('IDLE', 'LANG UNSUPPORTED');
            } else if (event.error === 'no-speech') {
                this.setState('IDLE', 'NO SPEECH DETECTED');
            } else if (event.error !== 'aborted') {
                this.showToast(`Speech error: ${event.error}`, true);
                this.setState('IDLE');
            }
        };

        this.recognition.onend = () => {
            this.isRecognitionActive = false;
            if (this.state === 'LISTENING') {
                this.setState('IDLE');
            }
        };
    }

    startListening() {
        if (!this.recognition) {
            this.showToast('Microphone not supported. Use text input below.', true);
            if (this.textInput) this.textInput.focus();
            return;
        }

        if (this.state === 'SPEAKING' || this.state === 'PAUSED') {
            this.stopAudioPlayback();
        }

        if (!this.isRecognitionActive) {
            try {
                this.recognition.start();
            } catch (e) {
                console.warn('Speech recognition start error:', e);
                try {
                    this.recognition.abort();
                    setTimeout(() => {
                        try { this.recognition.start(); } catch (err) {}
                    }, 150);
                } catch (err) {}
            }
        }
    }

    stopListening() {
        if (this.recognition && this.isRecognitionActive) {
            try {
                this.recognition.stop();
            } catch (e) {}
        }
        this.isRecognitionActive = false;
        if (this.state === 'LISTENING') {
            this.setState('IDLE');
        }
    }

    toggleListening() {
        if (this.isRecognitionActive) {
            this.stopListening();
        } else {
            this.startListening();
        }
    }

    /* ==========================================================================
       CONVERSATIONAL CHAT & BACKEND DISPATCH
       ========================================================================== */
    async handleUserMessage(message) {
        if (!message || !message.trim()) return;

        // Cleanly stop any existing speech before handling new message
        this.stopAudioPlayback();

        // Add user entry to JARVIS transcript feed
        this.addTranscriptEntry('user', 'YOU', message);

        // Also append immediately to underlying CareerBot chat stream
        if (window.careerbotAppendMessage) {
            window.careerbotAppendMessage('user', message);
        }

        // Transition to THINKING state
        this.setState('THINKING');

        try {
            const selectedLang = this.selectedLanguage || localStorage.getItem('careerbot_language') || 'en-IN';
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': getJarvisCsrfToken(),
                    'X-CSRFToken': getJarvisCsrfToken()
                },
                body: JSON.stringify({
                    message: message,
                    language: selectedLang
                })
            });

            const data = await response.json();

            if (!response.ok) {
                const errorMsg = data.error || 'Failed to process request.';
                this.showToast(errorMsg, true);
                this.addTranscriptEntry('assistant', 'JARVIS // ERROR', errorMsg);
                if (window.careerbotAppendMessage) {
                    window.careerbotAppendMessage('bot', `⚠️ ${errorMsg}`);
                }
                this.setState('IDLE');
                return;
            }

            const replyText = data.response || "I am standing by, sir.";
            const ttsText = data.tts_text || replyText;

            // Add complete response to JARVIS transcript feed
            this.addTranscriptEntry('assistant', 'JARVIS', replyText);

            // Also append complete response to underlying CareerBot chat stream
            if (window.careerbotAppendMessage) {
                window.careerbotAppendMessage('bot', replyText);
            }

            // Synthesize voice through ElevenLabs with cleaned text
            await this.playVoiceResponse(ttsText);

        } catch (error) {
            console.error('Chat request error:', error);
            this.showToast('Network error: Unable to reach CareerBot backend.', true);
            this.setState('IDLE');
        }
    }

    /* ==========================================================================
       ELEVENLABS TTS & AUDIO PLAYBACK
       ========================================================================== */
    async playVoiceResponse(text) {
        this.setState('SPEAKING');

        try {
            const selectedLang = this.selectedLanguage || localStorage.getItem('careerbot_language') || 'en-IN';
            const response = await fetch('/api/tts', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': getJarvisCsrfToken(),
                    'X-CSRFToken': getJarvisCsrfToken()
                },
                body: JSON.stringify({
                    text: text,
                    language: selectedLang
                })
            });

            if (!response.ok) {
                let errorMsg = 'Failed to generate voice speech.';
                try {
                    const errData = await response.json();
                    errorMsg = errData.error || errorMsg;
                } catch (e) {}

                console.warn('ElevenLabs TTS Notice:', errorMsg);
                // Fall back gracefully to browser speech synthesis
                this.speakWithBrowserFallback(text);
                return;
            }

            const audioBlob = await response.blob();
            const audioUrl = URL.createObjectURL(audioBlob);

            this.initAudioAnalyser(this.audioPlayer);

            this.audioPlayer.src = audioUrl;
            this.audioPlayer.onended = () => {
                URL.revokeObjectURL(audioUrl);
                this.setState('IDLE');
            };

            this.audioPlayer.onerror = (e) => {
                console.warn('Audio element error, falling back:', e);
                this.speakWithBrowserFallback(text);
            };

            await this.audioPlayer.play();

        } catch (error) {
            console.warn('TTS fetch failed, using browser speech synthesis:', error);
            this.speakWithBrowserFallback(text);
        }
    }

    speakWithBrowserFallback(text) {
        if (!('speechSynthesis' in window)) {
            this.setState('IDLE');
            return;
        }

        window.speechSynthesis.cancel();
        this.setState('SPEAKING');

        const utterance = new SpeechSynthesisUtterance(text);
        this.currentUtterance = utterance;
        utterance.rate = 1.0;
        utterance.pitch = 0.95;

        const lang = this.selectedLanguage || 'en-IN';
        const langPrefix = lang.split('-')[0].toLowerCase();
        const voices = window.speechSynthesis.getVoices();
        const preferredVoice = voices.find(v => v.lang.toLowerCase() === lang.toLowerCase() || v.lang.toLowerCase().startsWith(langPrefix)) ||
                               voices.find(v => v.lang.includes('en') && (v.name.includes('Male') || v.name.includes('Natural') || v.name.includes('India') || v.name.includes('George')));
        if (preferredVoice) {
            utterance.voice = preferredVoice;
            utterance.lang = preferredVoice.lang;
        } else {
            utterance.lang = lang;
        }

        utterance.onend = () => {
            this.currentUtterance = null;
            this.setState('IDLE');
        };
        utterance.onerror = (e) => {
            console.warn('Browser speech error:', e);
            this.currentUtterance = null;
            this.setState('IDLE');
        };

        window.speechSynthesis.speak(utterance);
    }

    togglePauseResume() {
        if (this.state === 'SPEAKING') {
            if (this.audioPlayer && !this.audioPlayer.paused) {
                this.audioPlayer.pause();
            }
            if ('speechSynthesis' in window && window.speechSynthesis.speaking && !window.speechSynthesis.paused) {
                window.speechSynthesis.pause();
            }
            this.setState('PAUSED');
        } else if (this.state === 'PAUSED') {
            if (this.audioPlayer && this.audioPlayer.src && this.audioPlayer.paused) {
                this.audioPlayer.play().catch(e => console.warn('Audio resume error:', e));
            }
            if ('speechSynthesis' in window && window.speechSynthesis.paused) {
                window.speechSynthesis.resume();
            }
            this.setState('SPEAKING');
        }
    }

    stopAudioPlayback() {
        if (this.audioPlayer) {
            this.audioPlayer.pause();
            this.audioPlayer.currentTime = 0;
            this.audioPlayer.removeAttribute('src');
        }
        if ('speechSynthesis' in window && (window.speechSynthesis.speaking || window.speechSynthesis.paused)) {
            window.speechSynthesis.cancel();
        }
        this.currentUtterance = null;
        if (this.state === 'SPEAKING' || this.state === 'PAUSED') {
            this.setState('IDLE');
        }
    }

    initAudioAnalyser(audioElement) {
        try {
            if (!this.audioCtx) {
                const AudioCtxClass = window.AudioContext || window.webkitAudioContext;
                if (!AudioCtxClass) return;
                this.audioCtx = new AudioCtxClass();
            }

            if (this.audioCtx.state === 'suspended') {
                this.audioCtx.resume();
            }

            if (!this.audioSource) {
                this.audioSource = this.audioCtx.createMediaElementSource(audioElement);
                this.analyser = this.audioCtx.createAnalyser();
                this.analyser.fftSize = 64;
                this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);

                this.audioSource.connect(this.analyser);
                this.analyser.connect(this.audioCtx.destination);
            }
        } catch (e) {
            // Analyser already connected or not supported
        }
    }

    /* ==========================================================================
       TRANSCRIPT & HUD TELEMETRY
       ========================================================================== */
    addTranscriptEntry(role, title, text) {
        if (!this.transcriptFeed) return;

        const entry = document.createElement('div');
        entry.className = `message-entry ${role}`;

        const istFormatter = new Intl.DateTimeFormat('en-IN', {
            timeZone: 'Asia/Kolkata',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });
        const istTime = `${istFormatter.format(new Date())} IST`;

        const meta = document.createElement('div');
        meta.className = 'message-meta';
        meta.textContent = `${title} • ${istTime}`;

        const body = document.createElement('div');
        body.className = 'message-text';
        body.textContent = text;

        entry.appendChild(meta);
        entry.appendChild(body);
        this.transcriptFeed.appendChild(entry);

        this.transcriptFeed.scrollTop = this.transcriptFeed.scrollHeight;
    }

    syncExistingCareerBotMessages() {
        if (!this.transcriptFeed) return;
        this.transcriptFeed.innerHTML = '';

        // Add intro message
        this.addTranscriptEntry('assistant', 'JARVIS • NEURAL CORE', 'All systems online, sir. Live voice interaction active.');

        // Grab historical rows from chatStream
        const stream = document.getElementById('chatStream');
        if (stream) {
            const rows = stream.querySelectorAll('.chat-message-row');
            rows.forEach(r => {
                const isUser = r.classList.contains('user');
                const textEl = r.querySelector('.chat-bubble > div');
                const text = textEl ? textEl.innerText.trim() : '';
                if (text && !text.startsWith('⚠️')) {
                    this.addTranscriptEntry(isUser ? 'user' : 'assistant', isUser ? 'YOU' : 'CAREERBOT', text);
                }
            });
        }
    }

    clearSession() {
        this.stopAudioPlayback();
        if (this.transcriptFeed) {
            this.transcriptFeed.innerHTML = '';
            this.addTranscriptEntry('assistant', 'JARVIS', 'Session memory reset. Conversation feed cleared.');
        }
        this.showToast('Session feed reset.');
    }

    showToast(message, isError = false) {
        if (!this.toast || !this.toastMessage) return;
        this.toastMessage.textContent = message;
        this.toast.className = `hud-toast visible ${isError ? 'toast-error' : ''}`;

        if (this._toastTimer) clearTimeout(this._toastTimer);
        this._toastTimer = setTimeout(() => {
            this.toast.classList.remove('visible');
        }, 5000);
    }

    async checkSystemHealth() {
        try {
            const resp = await fetch('/api/health');
            const data = await resp.json();

            if (this.statusDot && this.statusText) {
                if (data.gemini_configured || data.gemini === 'available') {
                    this.statusDot.className = 'status-dot active';
                    this.statusText.textContent = 'ONLINE // SECURE';
                } else {
                    this.statusDot.className = 'status-dot warn';
                    this.statusText.textContent = 'GEMINI KEY REQ';
                }
            }
        } catch (e) {
            if (this.statusDot && this.statusText) {
                this.statusDot.className = 'status-dot error';
                this.statusText.textContent = 'SERVER OFFLINE';
            }
        }
    }

    initClock() {
        const timeFormatter = new Intl.DateTimeFormat('en-IN', {
            timeZone: 'Asia/Kolkata',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });

        const updateClock = () => {
            const now = new Date();
            const timeStr = `${timeFormatter.format(now)} IST`;
            if (this.sysClock) this.sysClock.textContent = timeStr;
            if (this.coreFrequencyReadout) {
                this.coreFrequencyReadout.textContent = `${(44.1 + Math.sin(now.getTime() * 0.001) * 0.2).toFixed(1)} kHz`;
            }
        };
        updateClock();
        setInterval(updateClock, 1000);
    }

    /* ==========================================================================
       OPEN / EXIT LIVE MODE
       ========================================================================== */
    openLiveMode() {
        this.isOpen = true;
        this.overlay.classList.add('active');
        document.body.style.overflow = 'hidden';

        this.resizeCanvas();
        this.syncExistingCareerBotMessages();
        this.setState('IDLE');

        // Start render animation loop
        if (!this.animFrameId) {
            this.animFrameId = requestAnimationFrame((t) => this.render(t));
        }

        // Auto-start listening after short delay so user can speak immediately
        setTimeout(() => {
            if (this.isOpen && this.state === 'IDLE') {
                this.startListening();
            }
        }, 300);
    }

    exitLiveMode() {
        this.isOpen = false;
        this.stopListening();
        this.stopAudioPlayback();

        if (this.animFrameId) {
            cancelAnimationFrame(this.animFrameId);
            this.animFrameId = null;
        }

        this.overlay.classList.remove('active');
        document.body.style.overflow = '';

        // Scroll CareerBot chat stream to bottom so user immediately sees all responses
        const chatStream = document.getElementById('chatStream');
        if (chatStream) {
            chatStream.scrollTop = chatStream.scrollHeight;
        }
        const chatInput = document.getElementById('chatInput');
        if (chatInput) {
            chatInput.focus();
        }
    }

    setLanguage(langCode) {
        if (!langCode) return;
        this.selectedLanguage = langCode;
        localStorage.setItem('careerbot_language', langCode);

        if (this.langSelect && this.langSelect.value !== langCode) {
            this.langSelect.value = langCode;
        }
        const vSelect = document.getElementById('voiceLangSelect');
        if (vSelect && vSelect.value !== langCode) {
            vSelect.value = langCode;
        }

        if (this.recognition) {
            this.recognition.lang = langCode;
            if (this.isRecognitionActive) {
                this.stopListening();
                setTimeout(() => this.startListening(), 250);
            }
        }

        const langLabels = {
            'en-IN': 'English',
            'en-US': 'English (US)',
            'hi-IN': 'Hindi (हिन्दी)',
            'te-IN': 'Telugu (తెలుగు)',
            'ta-IN': 'Tamil (தமிழ்)',
            'kn-IN': 'Kannada (ಕನ್ನಡ)',
            'ml-IN': 'Malayalam (മലയാളം)'
        };
        const label = langLabels[langCode] || langCode;
        this.showToast(`Language set to ${label}`);
    }

    bindEvents() {
        // Language selector change in Jarvis HUD
        if (this.langSelect) {
            this.langSelect.addEventListener('change', () => {
                this.setLanguage(this.langSelect.value);
            });
        }

        // Microphone button click
        if (this.micBtn) {
            this.micBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleListening();
            });
        }

        // Pause / Resume button click
        if (this.pauseBtn) {
            this.pauseBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.togglePauseResume();
            });
        }

        // Exit Live Mode button click
        if (this.exitLiveBtn) {
            this.exitLiveBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.exitLiveMode();
            });
        }

        // Core stage click also toggles voice activation
        const coreStage = document.getElementById('core-stage');
        if (coreStage) {
            coreStage.addEventListener('click', () => {
                this.toggleListening();
            });
        }

        // Fallback text form submission
        if (this.textForm && this.textInput) {
            this.textForm.addEventListener('submit', (e) => {
                e.preventDefault();
                const text = this.textInput.value.trim();
                if (!text) return;
                this.textInput.value = '';
                this.handleUserMessage(text);
            });
        }

        // Reset session button
        if (this.clearHistoryBtn) {
            this.clearHistoryBtn.addEventListener('click', () => {
                this.clearSession();
            });
        }

        // Collapse / Expand Transcript drawer
        if (this.toggleTranscriptBtn) {
            this.toggleTranscriptBtn.addEventListener('click', () => {
                const isCollapsed = this.transcriptFeed.style.display === 'none';
                this.transcriptFeed.style.display = isCollapsed ? 'flex' : 'none';
                if (this.textForm) this.textForm.style.display = isCollapsed ? 'flex' : 'none';
                this.toggleTranscriptBtn.textContent = isCollapsed ? 'COLLAPSE' : 'EXPAND';
            });
        }

        // Allow Escape key to exit Live Mode safely
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.exitLiveMode();
            }
        });
    }
}

// Global initialization
window.jarvisHUD = null;
document.addEventListener('DOMContentLoaded', () => {
    window.jarvisHUD = new JarvisHUD();
});
