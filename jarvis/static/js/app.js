/**
 * JARVIS VOICE AI - CLIENT ENGINE
 * Handles:
 * - HTML5 Canvas Particle Orbit & Core Visualizer (IDLE, LISTENING, THINKING, SPEAKING)
 * - Web Speech API Speech Recognition
 * - Gemini API Conversational Orchestration (/api/chat)
 * - ElevenLabs Text-to-Speech Audio Stream & Real-time Web Audio Analyser (/api/tts)
 * - Session History & HUD UI Updates
 */

class JarvisHUD {
    constructor() {
        // UI Elements
        this.canvas = document.getElementById('jarvis-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.micBtn = document.getElementById('mic-btn');
        this.micCaption = document.getElementById('mic-caption');
        this.stateDisplay = document.getElementById('state-display');
        this.stateSubText = document.getElementById('state-sub-text');
        this.coreStateBadge = document.getElementById('core-state-badge');
        this.coreFrequencyReadout = document.getElementById('core-frequency-readout');
        this.transcriptFeed = document.getElementById('transcript-feed');
        this.textForm = document.getElementById('text-fallback-form');
        this.textInput = document.getElementById('text-input');
        this.clearHistoryBtn = document.getElementById('clear-history-btn');
        this.toggleTranscriptBtn = document.getElementById('toggle-transcript-btn');
        this.audioPlayer = document.getElementById('tts-audio-player');
        this.toast = document.getElementById('hud-toast');
        this.toastMessage = document.getElementById('toast-message');
        this.statusDot = document.getElementById('system-status-dot');
        this.statusText = document.getElementById('system-status-text');
        this.waveformContainer = document.getElementById('waveform-container');
        this.waveformBars = Array.from(document.querySelectorAll('.waveform-bar'));
        this.sysClock = document.getElementById('sys-clock');

        // Pause / Resume Control Elements
        this.pauseBtn = document.getElementById('pause-btn');
        this.pauseIcon = document.getElementById('pause-icon');
        this.playIcon = document.getElementById('play-icon');
        this.pauseBtnLabel = document.getElementById('pause-btn-label');

        // State machine: 'IDLE' | 'LISTENING' | 'THINKING' | 'SPEAKING' | 'PAUSED'
        this.state = 'IDLE';
        this.conversationHistory = [];
        this.recognition = null;
        this.isRecognitionActive = false;

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

        this.init();
    }

    async init() {
        this.resizeCanvas();
        window.addEventListener('resize', () => this.resizeCanvas());

        this.initParticles();
        this.initClock();
        this.initSpeechRecognition();
        this.bindEvents();
        this.checkSystemHealth();

        // Start render loop
        requestAnimationFrame((time) => this.render(time));
    }

    /* ==========================================================================
       CANVAS & PARTICLE SYSTEM
       ========================================================================== */
    resizeCanvas() {
        const rect = this.canvas.parentElement.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        this.canvas.width = rect.width * dpr;
        this.canvas.height = rect.height * dpr;
        this.ctx.scale(dpr, dpr);
        this.center = { x: rect.width / 2, y: rect.height / 2 };
    }

    initParticles() {
        this.particles = [];
        const baseRadius = 85;

        for (let i = 0; i < this.numParticles; i++) {
            // Distribute across orbital rings
            const ring = i % 4; // 4 orbital rings
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
        this.stateDisplay.textContent = newState;
        this.coreStateBadge.textContent = newState;

        // Update UI descriptions
        if (subText) {
            this.stateSubText.textContent = subText;
        } else {
            switch (newState) {
                case 'IDLE':
                    this.stateSubText.textContent = 'STANDBY // READY FOR INPUT';
                    break;
                case 'LISTENING':
                    this.stateSubText.textContent = 'RECEIVING AUDIO STREAM...';
                    break;
                case 'THINKING':
                    this.stateSubText.textContent = 'GEMINI NEURAL PROCESSING...';
                    break;
                case 'SPEAKING':
                    this.stateSubText.textContent = 'ELEVENLABS VOICE TRANSMISSION';
                    break;
                case 'PAUSED':
                    this.stateSubText.textContent = 'AUDIO SUSPENDED // CLICK RESUME';
                    break;
            }
        }

        // State styles for Core Readout & State Display
        if (newState === 'PAUSED') {
            this.coreStateBadge.classList.add('state-paused');
            this.stateDisplay.classList.add('state-paused');
        } else {
            this.coreStateBadge.classList.remove('state-paused');
            this.stateDisplay.classList.remove('state-paused');
        }

        // State styles for Microphone
        if (newState === 'LISTENING') {
            this.micBtn.classList.add('listening');
            this.micCaption.textContent = 'CLICK TO STOP LISTENING';
            this.waveformContainer.classList.add('active');
        } else {
            this.micBtn.classList.remove('listening');
            if (newState !== 'SPEAKING') {
                this.waveformContainer.classList.remove('active');
            }
            if (newState === 'SPEAKING') {
                this.micCaption.textContent = 'JARVIS IS SPEAKING';
            } else if (newState === 'PAUSED') {
                this.micCaption.textContent = 'SPEECH PAUSED • CLICK RESUME TO CONTINUE';
            } else {
                this.micCaption.textContent = 'CLICK TO ACTIVATE VOICE';
            }
        }

        // State styles for Pause / Resume Button
        if (this.pauseBtn) {
            if (newState === 'SPEAKING') {
                this.pauseBtn.disabled = false;
                this.pauseBtn.classList.add('speaking');
                this.pauseBtn.classList.remove('is-paused');
                this.pauseIcon.style.display = 'block';
                this.playIcon.style.display = 'none';
                this.pauseBtnLabel.textContent = 'PAUSE';
                this.pauseBtn.setAttribute('title', 'Pause speech');
            } else if (newState === 'PAUSED') {
                this.pauseBtn.disabled = false;
                this.pauseBtn.classList.remove('speaking');
                this.pauseBtn.classList.add('is-paused');
                this.pauseIcon.style.display = 'none';
                this.playIcon.style.display = 'block';
                this.pauseBtnLabel.textContent = 'RESUME';
                this.pauseBtn.setAttribute('title', 'Resume speech');
            } else {
                // IDLE, LISTENING, THINKING
                this.pauseBtn.disabled = true;
                this.pauseBtn.classList.remove('speaking', 'is-paused');
                this.pauseIcon.style.display = 'block';
                this.playIcon.style.display = 'none';
                this.pauseBtnLabel.textContent = 'PAUSE';
                this.pauseBtn.setAttribute('title', 'Pause speech');
            }
        }
    }

    render(time) {
        const ctx = this.ctx;
        const width = this.canvas.width / (window.devicePixelRatio || 1);
        const height = this.canvas.height / (window.devicePixelRatio || 1);
        const cx = this.center.x;
        const cy = this.center.y;

        ctx.clearRect(0, 0, width, height);

        // Calculate audio reactivity level
        let audioReact = 0;
        if (this.state === 'SPEAKING' && this.analyser && this.dataArray) {
            this.analyser.getByteFrequencyData(this.dataArray);
            let sum = 0;
            for (let i = 0; i < 32; i++) {
                sum += this.dataArray[i];
            }
            audioReact = (sum / 32) / 255; // 0.0 to 1.0
        } else if (this.state === 'LISTENING') {
            audioReact = 0.25 + Math.sin(time * 0.008) * 0.15;
        } else if (this.state === 'SPEAKING') {
            // Fallback audio simulation if AudioContext not active
            audioReact = 0.4 + Math.sin(time * 0.012) * 0.3 * Math.cos(time * 0.007);
        } else if (this.state === 'PAUSED') {
            audioReact = 0; // Flatline while paused
        }

        // Update waveform bars
        this.updateWaveformBars(audioReact);

        // Core Breathing / Pulse Phase
        if (this.state !== 'PAUSED') {
            this.pulsePhase += this.state === 'THINKING' ? 0.08 : (this.state === 'SPEAKING' ? 0.06 : 0.02);
        }

        // 1. Draw Central Arc Reactor Core
        this.drawArcReactorCore(ctx, cx, cy, audioReact, time);

        // 2. Draw Orbiting Particle Swarm
        this.drawParticles(ctx, cx, cy, audioReact, time);

        // 3. Draw Rotating HUD Arcs & Brackets
        this.drawHudArcs(ctx, cx, cy, time);

        requestAnimationFrame((t) => this.render(t));
    }

    drawArcReactorCore(ctx, cx, cy, audioReact, time) {
        ctx.save();

        let baseCoreRadius = 45;
        if (this.state === 'LISTENING') baseCoreRadius = 48 + audioReact * 12;
        else if (this.state === 'THINKING') baseCoreRadius = 44 + Math.sin(time * 0.01) * 6;
        else if (this.state === 'SPEAKING') baseCoreRadius = 46 + audioReact * 24;
        else if (this.state === 'PAUSED') baseCoreRadius = 44;

        // Core Outer Glow
        const glowRadius = baseCoreRadius * 1.8;
        const radialGlow = ctx.createRadialGradient(cx, cy, baseCoreRadius * 0.5, cx, cy, glowRadius);
        if (this.state === 'PAUSED') {
            radialGlow.addColorStop(0, 'rgba(255, 170, 0, 0.35)');
            radialGlow.addColorStop(0.5, 'rgba(255, 170, 0, 0.1)');
            radialGlow.addColorStop(1, 'rgba(255, 170, 0, 0)');
        } else {
            radialGlow.addColorStop(0, 'rgba(0, 240, 255, 0.4)');
            radialGlow.addColorStop(0.5, 'rgba(0, 240, 255, 0.12)');
            radialGlow.addColorStop(1, 'rgba(0, 240, 255, 0)');
        }

        ctx.fillStyle = radialGlow;
        ctx.beginPath();
        ctx.arc(cx, cy, glowRadius, 0, Math.PI * 2);
        ctx.fill();

        // Center Ring
        ctx.beginPath();
        ctx.arc(cx, cy, baseCoreRadius, 0, Math.PI * 2);
        if (this.state === 'LISTENING') {
            ctx.strokeStyle = '#00ffaa';
            ctx.shadowColor = '#00ffaa';
        } else if (this.state === 'PAUSED') {
            ctx.strokeStyle = '#ffaa00';
            ctx.shadowColor = '#ffaa00';
        } else {
            ctx.strokeStyle = 'rgba(0, 240, 255, 0.85)';
            ctx.shadowColor = '#00f0ff';
        }
        ctx.lineWidth = 2;
        ctx.shadowBlur = 12;
        ctx.stroke();

        // Inner Concentric Ring
        ctx.beginPath();
        ctx.arc(cx, cy, baseCoreRadius * 0.72, 0, Math.PI * 2);
        ctx.strokeStyle = this.state === 'PAUSED' ? 'rgba(255, 170, 0, 0.4)' : 'rgba(0, 240, 255, 0.35)';
        ctx.lineWidth = 1.5;
        ctx.stroke();

        ctx.restore();
    }

    drawParticles(ctx, cx, cy, audioReact, time) {
        ctx.save();

        // State speed & expansion multipliers
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
            speedMultiplier = 0.08; // Suspended gentle drift
            radiusOffset = 0;
        }

        for (let i = 0; i < this.particles.length; i++) {
            const p = this.particles[i];

            // Update angle
            p.angle += p.baseSpeed * speedMultiplier;
            p.wobble += p.wobbleSpeed * (this.state === 'PAUSED' ? 0.1 : 1.0);

            // Compute current orbit radius with wobble & audio reaction
            const currentRadius = p.baseRadius + radiusOffset + Math.sin(p.wobble) * 6;
            const px = cx + Math.cos(p.angle) * currentRadius;
            const py = cy + Math.sin(p.angle) * currentRadius;

            // Draw connecting energy lines between nearby particles in the same ring
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
                    const lineColor = this.state === 'PAUSED' ? `rgba(255, 170, 0, ${(1 - dist / 70) * 0.2})` : `rgba(0, 240, 255, ${(1 - dist / 70) * 0.25})`;
                    ctx.strokeStyle = lineColor;
                    ctx.lineWidth = 0.8;
                    ctx.stroke();
                }
            }

            // Draw glowing particle dot
            ctx.beginPath();
            const pSize = p.size * (1 + (audioReact * 0.8));
            ctx.arc(px, py, pSize, 0, Math.PI * 2);

            let particleColor = 'rgba(0, 240, 255, ';
            if (this.state === 'LISTENING') {
                particleColor = 'rgba(0, 255, 170, ';
            } else if (this.state === 'THINKING') {
                particleColor = 'rgba(112, 247, 255, ';
            } else if (this.state === 'PAUSED') {
                particleColor = 'rgba(255, 170, 0, ';
            }

            ctx.fillStyle = `${particleColor}${p.opacity})`;
            ctx.shadowColor = this.state === 'PAUSED' ? '#ffaa00' : '#00f0ff';
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
        ctx.strokeStyle = this.state === 'PAUSED' ? 'rgba(255, 170, 0, 0.4)' : 'rgba(0, 240, 255, 0.4)';
        ctx.lineWidth = 1.5;
        ctx.stroke();

        ctx.beginPath();
        ctx.arc(cx, cy, 64, angleOffset + Math.PI, angleOffset + Math.PI * 1.8);
        ctx.strokeStyle = this.state === 'PAUSED' ? 'rgba(255, 170, 0, 0.4)' : 'rgba(0, 240, 255, 0.4)';
        ctx.lineWidth = 1.5;
        ctx.stroke();
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Outer Notched Compass Arcs
        const outerAngle = -time * 0.003;
        ctx.beginPath();
        ctx.arc(cx, cy, 195, outerAngle, outerAngle + Math.PI * 0.35);
        ctx.strokeStyle = 'rgba(0, 240, 255, 0.25)';
        ctx.lineWidth = 2;
        ctx.stroke();

        ctx.beginPath();
        ctx.arc(cx, cy, 195, outerAngle + Math.PI, outerAngle + Math.PI * 1.35);
        ctx.strokeStyle = 'rgba(0, 240, 255, 0.25)';
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
            this.showToast('Microphone API not supported by browser. Use text input below.', true);
            this.statusDot.className = 'status-dot warn';
            this.statusText.textContent = 'MIC UNSUPPORTED';
            return;
        }

        this.recognition = new SpeechRecognition();
        this.recognition.continuous = false;
        this.recognition.interimResults = false;
        this.recognition.lang = 'en-US';

        this.recognition.onstart = () => {
            this.isRecognitionActive = true;
            this.setState('LISTENING');
        };

        this.recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            console.log('Recognized speech:', transcript);
            if (transcript && transcript.trim()) {
                this.handleUserMessage(transcript.trim());
            }
        };

        this.recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            this.isRecognitionActive = false;

            if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
                this.showToast('Microphone access denied. Please grant microphone permission in your browser.', true);
                this.setState('IDLE', 'MIC ACCESS DENIED');
            } else if (event.error === 'no-speech') {
                this.setState('IDLE', 'NO SPEECH DETECTED');
            } else {
                this.showToast(`Speech recognition error: ${event.error}`, true);
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

    toggleListening() {
        if (!this.recognition) {
            this.showToast('Microphone not supported. Please type your message in the terminal.', true);
            this.textInput.focus();
            return;
        }

        // If audio is currently speaking or paused, stop it cleanly
        if (this.state === 'SPEAKING' || this.state === 'PAUSED') {
            this.stopAudioPlayback();
        }

        if (this.isRecognitionActive) {
            try {
                this.recognition.stop();
            } catch (e) {
                console.error('Error stopping recognition:', e);
            }
            this.isRecognitionActive = false;
            this.setState('IDLE');
        } else {
            try {
                this.recognition.start();
            } catch (e) {
                console.error('Error starting recognition:', e);
                // Already started or busy, reset
                try {
                    this.recognition.abort();
                    setTimeout(() => this.recognition.start(), 150);
                } catch (err) {
                    this.showToast('Microphone error: ' + err.message, true);
                }
            }
        }
    }

    /* ==========================================================================
       CONVERSATIONAL CHAT & GEMINI API
       ========================================================================== */
    async handleUserMessage(message) {
        if (!message || !message.trim()) return;

        // Cleanly stop any existing speech before handling new message
        this.stopAudioPlayback();

        // Add user entry to transcript feed
        this.addTranscriptEntry('user', 'YOU', message);

        // Transition to THINKING state
        this.setState('THINKING');

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: message,
                    history: this.conversationHistory
                })
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                const errorMsg = data.error || 'Failed to process request with Gemini.';
                this.showToast(errorMsg, true);
                this.addTranscriptEntry('assistant', 'JARVIS // ERROR', errorMsg);
                this.setState('IDLE');
                return;
            }

            const jarvisReply = data.response;
            const jarvisTtsText = data.tts_text || jarvisReply;
            this.conversationHistory = data.history || [];

            // Add complete response to transcript feed
            this.addTranscriptEntry('assistant', 'JARVIS', jarvisReply);

            // Trigger Voice Speech Synthesis using natural spoken speech text (tts_text)
            await this.playVoiceResponse(jarvisTtsText);

        } catch (error) {
            console.error('Network or chat error:', error);
            this.showToast('Network error: Unable to reach JARVIS backend.', true);
            this.setState('IDLE');
        }
    }

    /* ==========================================================================
       ELEVENLABS TTS & AUDIO PLAYBACK
       ========================================================================== */
    async playVoiceResponse(text) {
        this.setState('SPEAKING');

        try {
            // Send complete Gemini response to ElevenLabs
            const response = await fetch('/api/tts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: text })
            });

            if (!response.ok) {
                let errorMsg = 'Failed to generate voice speech.';
                let isPlanLimitation = false;
                try {
                    const errData = await response.json();
                    errorMsg = errData.error || errorMsg;
                    isPlanLimitation = Boolean(errData.is_plan_limitation);
                } catch (e) {
                    // Non-json error
                }

                if (isPlanLimitation || errorMsg.includes('Plan Limitation') || errorMsg.includes('Voice Library')) {
                    // Report as an ElevenLabs subscription/plan limitation rather than a code error
                    console.info('ElevenLabs Plan Notice:', errorMsg);
                    this.showToast(errorMsg, false);
                    this.statusDot.className = 'status-dot warn';
                    this.statusText.textContent = 'ELEVENLABS: PLAN ACCESS REQ';
                } else {
                    console.warn('ElevenLabs TTS error:', errorMsg);
                    this.showToast(`Voice Note: ${errorMsg}`, true);
                }

                // Play the complete response through local speech synthesis fallback
                this.speakWithBrowserFallback(text);
                return;
            }

            const audioBlob = await response.blob();
            const audioUrl = URL.createObjectURL(audioBlob);

            // Connect Web Audio API Analyser for live particle pulsing
            this.initAudioAnalyser(this.audioPlayer);

            this.audioPlayer.src = audioUrl;
            this.audioPlayer.onended = () => {
                URL.revokeObjectURL(audioUrl);
                this.setState('IDLE');
            };

            this.audioPlayer.onerror = (e) => {
                console.error('Audio playback error:', e);
                this.setState('IDLE');
                this.showToast('Audio playback error.', true);
            };

            await this.audioPlayer.play();

        } catch (error) {
            console.error('TTS request failed:', error);
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
        this.currentUtterance = utterance; // Retain reference to prevent GC interruption on long responses
        utterance.rate = 1.0;
        utterance.pitch = 0.95;

        // Select a natural English voice if available
        const voices = window.speechSynthesis.getVoices();
        const preferredVoice = voices.find(v => v.lang.includes('en') && (v.name.includes('Male') || v.name.includes('Natural') || v.name.includes('UK') || v.name.includes('George') || v.name.includes('India')));
        if (preferredVoice) utterance.voice = preferredVoice;

        utterance.onend = () => {
            this.currentUtterance = null;
            this.setState('IDLE');
        };
        utterance.onerror = (e) => {
            console.warn('SpeechSynthesis event:', e);
            this.currentUtterance = null;
            this.setState('IDLE');
        };

        window.speechSynthesis.speak(utterance);
    }

    togglePauseResume() {
        if (this.state === 'SPEAKING') {
            // Immediately pause audio without losing position or regenerating
            if (this.audioPlayer && !this.audioPlayer.paused) {
                this.audioPlayer.pause();
            }
            if ('speechSynthesis' in window && window.speechSynthesis.speaking && !window.speechSynthesis.paused) {
                window.speechSynthesis.pause();
            }
            this.setState('PAUSED');
        } else if (this.state === 'PAUSED') {
            // Resume audio from exact position
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
            console.warn('AudioContext setup skipped or already connected:', e);
        }
    }

    /* ==========================================================================
       TRANSCRIPT & HUD TELEMETRY
       ========================================================================== */
    addTranscriptEntry(role, title, text) {
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
        body.textContent = text; // Complete untruncated text

        entry.appendChild(meta);
        entry.appendChild(body);
        this.transcriptFeed.appendChild(entry);

        // Auto-scroll to bottom
        this.transcriptFeed.scrollTop = this.transcriptFeed.scrollHeight;
    }

    clearSession() {
        this.conversationHistory = [];
        this.stopAudioPlayback();
        this.transcriptFeed.innerHTML = '';
        this.addTranscriptEntry('assistant', 'JARVIS', 'Session memory reset. Conversation history cleared.');
        this.showToast('Session history cleared.');
    }

    showToast(message, isError = false) {
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

            if (data.gemini_configured) {
                this.statusDot.className = 'status-dot active';
                this.statusText.textContent = 'ONLINE // SECURE';
            } else {
                this.statusDot.className = 'status-dot warn';
                this.statusText.textContent = 'GEMINI KEY REQ';
                this.showToast('Configure GEMINI_API_KEY in .env for live AI responses.', true);
            }
        } catch (e) {
            this.statusDot.className = 'status-dot error';
            this.statusText.textContent = 'SERVER OFFLINE';
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
            this.sysClock.textContent = timeStr;
            this.coreFrequencyReadout.textContent = `${(44.1 + Math.sin(now.getTime() * 0.001) * 0.2).toFixed(1)} kHz`;
        };
        updateClock();
        setInterval(updateClock, 1000);
    }

    bindEvents() {
        // Microphone button click
        this.micBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggleListening();
        });

        // Pause / Resume button click
        if (this.pauseBtn) {
            this.pauseBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.togglePauseResume();
            });
        }

        // Core stage click also toggles voice activation
        document.getElementById('core-stage').addEventListener('click', () => {
            this.toggleListening();
        });

        // Fallback text form submission
        this.textForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const text = this.textInput.value.trim();
            if (!text) return;

            this.textInput.value = '';
            this.handleUserMessage(text);
        });

        // Reset session
        this.clearHistoryBtn.addEventListener('click', () => {
            this.clearSession();
        });

        // Collapse / Expand Transcript drawer
        this.toggleTranscriptBtn.addEventListener('click', () => {
            const isCollapsed = this.transcriptFeed.style.display === 'none';
            this.transcriptFeed.style.display = isCollapsed ? 'flex' : 'none';
            this.textForm.style.display = isCollapsed ? 'flex' : 'none';
            this.toggleTranscriptBtn.textContent = isCollapsed ? 'COLLAPSE' : 'EXPAND';
        });
    }
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
    window.jarvis = new JarvisHUD();
});
