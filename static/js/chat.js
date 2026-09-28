/* ======================================================
   CareerBot ChatGPT/Gemini Style Interface & Voice Assistant
   Two-Way Speech Recognition & Text-to-Speech Playback
   ====================================================== */

let recognition = null;
let isListening = false;
let currentUtterance = null;
let availableVoices = [];

// Initialize SpeechSynthesis Voices
function loadVoices() {
    if ('speechSynthesis' in window) {
        availableVoices = window.speechSynthesis.getVoices();
    }
}

if ('speechSynthesis' in window) {
    loadVoices();
    if (window.speechSynthesis.onvoiceschanged !== undefined) {
        window.speechSynthesis.onvoiceschanged = loadVoices;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const chatStream = document.getElementById('chatStream');
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendBtn');
    const micBtn = document.getElementById('micBtn');
    const emptyState = document.getElementById('emptyState');
    const clearChatBtn = document.getElementById('clearChatBtn');
    const voiceModeToggle = document.getElementById('voiceModeToggle');
    const voiceLangSelect = document.getElementById('voiceLangSelect');

    if (!chatStream || !chatInput || !sendBtn) return;

    // Load Voice Mode preference
    if (voiceModeToggle) {
        const savedVoiceMode = localStorage.getItem('voice_mode') === 'true';
        voiceModeToggle.checked = savedVoiceMode;
        voiceModeToggle.addEventListener('change', () => {
            localStorage.setItem('voice_mode', voiceModeToggle.checked);
        });
    }

    scrollToBottom();
    if (window.lucide) lucide.createIcons();

    // Auto-resize composer input
    chatInput.addEventListener('input', () => {
        chatInput.style.height = 'auto';
        chatInput.style.height = Math.min(chatInput.scrollHeight, 140) + 'px';
    });

    // Enter sends message, Shift+Enter creates new line
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    sendBtn.addEventListener('click', (e) => {
        e.preventDefault();
        sendMessage();
    });

    // Prompt Chips Handler
    document.querySelectorAll('.prompt-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            const promptText = chip.getAttribute('data-prompt') || chip.innerText.trim();
            chatInput.value = promptText;
            sendMessage();
        });
    });

    // Clear Chat Handler
    if (clearChatBtn) {
        clearChatBtn.addEventListener('click', async () => {
            if (confirm("Are you sure you want to clear your chat history?")) {
                try {
                    const response = await fetch('/api/chat/clear', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRF-Token': getCsrfToken()
                        }
                    });
                    if (response.ok) {
                        chatStream.innerHTML = '';
                        if (emptyState) emptyState.style.display = 'block';
                    }
                } catch (err) {
                    console.error('Error clearing chat:', err);
                }
            }
        });
    }

    // Voice Input (Speech-to-Text) Initialization using native Web Speech API
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    function getSelectedSpeechLang() {
        if (!voiceLangSelect) return 'en-IN';
        const val = voiceLangSelect.value;
        const validCodes = ['en-IN', 'en-US', 'hi-IN', 'te-IN'];
        return validCodes.includes(val) ? val : 'en-IN';
    }

    // Voice Language Selector Listener
    if (voiceLangSelect) {
        voiceLangSelect.addEventListener('change', () => {
            if (recognition && isListening) {
                try { recognition.stop(); } catch (e) {}
                stopListening();
            }
        });
    }

    function createRecognitionInstance() {
        if (!SpeechRecognition) return null;

        const instance = new SpeechRecognition();
        instance.continuous = false;
        instance.interimResults = true;
        instance.maxAlternatives = 1;
        instance.lang = getSelectedSpeechLang();

        let initialInputValue = '';

        instance.onstart = () => {
            isListening = true;
            stopSpeechSynthesis(); // Prevent mic feedback loop
            setVoiceState('listening');
            initialInputValue = chatInput.value ? chatInput.value.trim() + ' ' : '';
        };

        instance.onresult = (event) => {
            let interimTranscript = '';
            let finalTranscript = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript;
                } else {
                    interimTranscript += transcript;
                }
            }
            const currentSpoken = finalTranscript || interimTranscript;
            chatInput.value = initialInputValue + currentSpoken;
            chatInput.style.height = 'auto';
            chatInput.style.height = Math.min(chatInput.scrollHeight, 140) + 'px';
        };

        instance.onerror = async (event) => {
            stopListening();
            const err = event.error;

            switch (err) {
                case 'not-allowed':
                case 'permission-denied': {
                    // Check actual browser permission state before displaying an incorrect banner
                    let isActuallyGranted = false;
                    if (navigator.permissions && navigator.permissions.query) {
                        try {
                            const p = await navigator.permissions.query({ name: 'microphone' });
                            if (p && p.state === 'granted') {
                                isActuallyGranted = true;
                            }
                        } catch (e) {}
                    }

                    if (isActuallyGranted) {
                        // Permission is already granted; device capture or audio stream encountered a temporary contention
                        showVoiceErrorBanner("Microphone audio device is currently busy. Please click the microphone again to retry.");
                    } else {
                        showVoiceErrorBanner("Microphone permission was denied. Please allow microphone access for this site in your browser settings.");
                    }
                    break;
                }
                case 'audio-capture':
                    showVoiceErrorBanner("No working microphone was detected on this device.");
                    break;
                case 'no-speech':
                    showVoiceInfoBanner("No speech was detected. Please click the microphone and try speaking again.");
                    break;
                case 'network':
                    showVoiceErrorBanner("Speech recognition service network error. Please verify your internet connection.");
                    break;
                case 'language-not-supported':
                    showVoiceErrorBanner(`Speech recognition is not supported for language (${instance.lang}) in this browser.`);
                    break;
                case 'service-not-allowed':
                    showVoiceErrorBanner("Speech recognition service is not allowed by this browser or operating system.");
                    break;
                case 'aborted':
                    // Clean cancellation without showing error
                    break;
                default:
                    showVoiceErrorBanner(`Speech recognition error: ${err}`);
                    break;
            }
        };

        instance.onend = () => {
            stopListening();
            if (chatInput) {
                chatInput.focus();
            }
        };

        return instance;
    }

    if (micBtn) {
        micBtn.addEventListener('click', (e) => {
            e.preventDefault();
            if (!SpeechRecognition) {
                clearVoiceBanners();
                showVoiceErrorBanner("Speech recognition is not supported in this browser. Please use Google Chrome or Microsoft Edge.");
                return;
            }

            if (isListening) {
                if (recognition) {
                    try { recognition.stop(); } catch (err) {}
                }
                stopListening();
            } else {
                startVoiceRecognition();
            }
        });
    }

    function startVoiceRecognition() {
        if (isListening) return;
        clearVoiceBanners();

        if (recognition) {
            try { recognition.stop(); } catch (e) {}
            try { recognition.abort(); } catch (e) {}
        }

        recognition = createRecognitionInstance();
        if (!recognition) return;

        try {
            isListening = true;
            setVoiceState('listening');
            recognition.start();
        } catch (e) {
            console.warn("SpeechRecognition start error:", e);
            stopListening();
            if (e.name === 'InvalidStateError') {
                return;
            }
            if (e.name === 'NotAllowedError' || e.name === 'PermissionDeniedError') {
                showVoiceErrorBanner("Microphone permission was denied. Please allow microphone access for this site.");
            } else {
                showVoiceErrorBanner(`Unable to start speech recognition: ${e.message || e.name}`);
            }
        }
    }

    function stopListening() {
        isListening = false;
        setVoiceState('idle');
    }

    function setVoiceState(state) {
        if (!micBtn) return;
        if (state === 'listening') {
            micBtn.classList.add('listening');
            micBtn.title = 'Listening... Click to stop';
        } else {
            micBtn.classList.remove('listening');
            micBtn.title = 'Start voice input';
        }
    }

    async function sendMessage() {
        const messageText = chatInput.value.trim();
        if (!messageText) return;

        if (emptyState) emptyState.style.display = 'none';

        // Reset input field height & clear text
        chatInput.value = '';
        chatInput.style.height = 'auto';

        // Disable send button temporarily to prevent duplicate submissions
        sendBtn.disabled = true;

        // Stop any active speech output
        stopSpeechSynthesis();

        appendMessage('user', messageText);
        scrollToBottom();

        const typingId = showTypingIndicator();
        scrollToBottom();

        try {
            const selectedLang = voiceLangSelect ? voiceLangSelect.value : 'en-IN';
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': getCsrfToken()
                },
                body: JSON.stringify({
                    message: messageText,
                    language: selectedLang
                })
            });

            removeTypingIndicator(typingId);

            if (response.ok) {
                const data = await response.json();
                const botReply = data.response || "No response received.";
                appendMessage('bot', botReply);

                // Auto-read aloud if Voice Mode is enabled
                if (voiceModeToggle && voiceModeToggle.checked) {
                    speakText(botReply);
                }
            } else {
                const errData = await response.json().catch(() => ({}));
                appendMessage('bot', `⚠️ ${errData.error || "CareerBot could not process your request. Please try again."}`);
            }
        } catch (error) {
            removeTypingIndicator(typingId);
            appendMessage('bot', "⚠️ Connection error. Please check your network and try again.");
        } finally {
            sendBtn.disabled = false;
            scrollToBottom();
        }
    }

    function appendMessage(sender, text) {
        const row = document.createElement('div');
        row.className = `chat-message-row ${sender}`;
        const isBot = sender === 'bot';
        const escapedText = escapeHtml(text).replace(/\n/g, '<br>');

        row.innerHTML = `
            ${isBot ? `
                <div class="bot-avatar">
                    <i data-lucide="bot" style="width: 18px; height: 18px;"></i>
                </div>
            ` : ''}
            <div class="chat-bubble">
                <div style="white-space: pre-wrap;">${escapedText}</div>
                ${isBot ? `
                    <div class="mt-2 text-end d-flex align-items-center justify-content-end gap-2">
                        <button class="btn btn-sm btn-link text-muted p-0 speak-btn" onclick="speakMessageText(this)" title="Listen to message">
                            <i data-lucide="volume-2" style="width: 14px; height: 14px;"></i> Listen
                        </button>
                        <button class="btn btn-sm btn-link text-muted p-0 me-2 copy-btn" onclick="copyMessageText(this)" title="Copy text">
                            <i data-lucide="copy" style="width: 14px; height: 14px;"></i> Copy
                        </button>
                    </div>
                ` : ''}
            </div>
        `;

        chatStream.appendChild(row);
        if (window.lucide) lucide.createIcons();
    }

    function showTypingIndicator() {
        const id = 'typing_' + Date.now();
        const row = document.createElement('div');
        row.className = 'chat-message-row bot';
        row.id = id;
        row.innerHTML = `
            <div class="bot-avatar">
                <i data-lucide="bot" style="width: 18px; height: 18px;"></i>
            </div>
            <div class="chat-bubble">
                <div class="typing-indicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        `;
        chatStream.appendChild(row);
        if (window.lucide) lucide.createIcons();
        return id;
    }

    function removeTypingIndicator(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    function scrollToBottom() {
        chatStream.scrollTop = chatStream.scrollHeight;
    }

    function clearVoiceBanners() {
        document.querySelectorAll('.voice-error-banner, .voice-info-banner').forEach(el => el.remove());
    }

    function showVoiceErrorBanner(message) {
        const existing = document.querySelector('.voice-error-banner');
        if (existing && existing.textContent.includes(message)) {
            return;
        }
        clearVoiceBanners();
        const banner = document.createElement('div');
        banner.className = 'alert alert-warning alert-dismissible fade show border-0 shadow-sm my-2 voice-error-banner';
        banner.innerHTML = `
            <i data-lucide="alert-triangle" style="width: 16px; height: 16px;" class="me-2"></i> ${escapeHtml(message)}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        chatStream.appendChild(banner);
        if (window.lucide) lucide.createIcons();
        scrollToBottom();
    }

    function showVoiceInfoBanner(message) {
        clearVoiceBanners();
        const banner = document.createElement('div');
        banner.className = 'alert alert-info alert-dismissible fade show border-0 shadow-sm my-2 voice-info-banner';
        banner.innerHTML = `
            <i data-lucide="info" style="width: 16px; height: 16px;" class="me-2"></i> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        chatStream.appendChild(banner);
        if (window.lucide) lucide.createIcons();
        scrollToBottom();
        setTimeout(() => {
            if (banner && banner.parentNode) banner.remove();
        }, 4000);
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.innerText = text;
        return div.innerHTML;
    }
});

// Copy Chat Message Helper
function copyMessageText(btn) {
    const bubble = btn.closest('.chat-bubble');
    if (bubble) {
        const text = bubble.querySelector('div').innerText;
        navigator.clipboard.writeText(text).then(() => {
            btn.innerHTML = `<i data-lucide="check" style="width: 14px; height: 14px;"></i> Copied`;
            if (window.lucide) lucide.createIcons();
            setTimeout(() => {
                btn.innerHTML = `<i data-lucide="copy" style="width: 14px; height: 14px;"></i> Copy`;
                if (window.lucide) lucide.createIcons();
            }, 2000);
        });
    }
}

// Text-to-Speech Playback Helper
function speakMessageText(btn) {
    const bubble = btn.closest('.chat-bubble');
    if (bubble) {
        const textContent = bubble.querySelector('div').innerText;
        if (window.speechSynthesis.speaking) {
            window.speechSynthesis.cancel();
            btn.innerHTML = `<i data-lucide="volume-2" style="width: 14px; height: 14px;"></i> Listen`;
            if (window.lucide) lucide.createIcons();
            return;
        }
        speakText(textContent, btn);
    }
}

function speakText(text, btn = null) {
    if (!('speechSynthesis' in window)) return;

    stopSpeechSynthesis();

    const cleanText = text.replace(/[*_#`~]/g, '');
    currentUtterance = new SpeechSynthesisUtterance(cleanText);
    currentUtterance.rate = 1.0;
    currentUtterance.pitch = 1.0;

    // Pick best available voice for language preference
    const voiceLangSelect = document.getElementById('voiceLangSelect');
    const selectedLang = voiceLangSelect ? voiceLangSelect.value : 'en-IN';
    if (availableVoices && availableVoices.length > 0) {
        const matchingVoice = availableVoices.find(v => v.lang === selectedLang || v.lang.startsWith(selectedLang.split('-')[0]));
        if (matchingVoice) {
            currentUtterance.voice = matchingVoice;
        }
    }

    const stopBtn = document.getElementById('stopSpeakingBtn');
    if (stopBtn) stopBtn.classList.remove('d-none');

    if (btn) {
        btn.innerHTML = `<span class="speaking-pulse">● Speaking...</span>`;
    }

    currentUtterance.onend = () => {
        if (stopBtn) stopBtn.classList.add('d-none');
        if (btn) {
            btn.innerHTML = `<i data-lucide="volume-2" style="width: 14px; height: 14px;"></i> Listen`;
            if (window.lucide) lucide.createIcons();
        }
    };

    currentUtterance.onerror = () => {
        if (stopBtn) stopBtn.classList.add('d-none');
        if (btn) {
            btn.innerHTML = `<i data-lucide="volume-2" style="width: 14px; height: 14px;"></i> Listen`;
            if (window.lucide) lucide.createIcons();
        }
    };

    window.speechSynthesis.speak(currentUtterance);
}

function stopSpeechSynthesis() {
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
    }
    const stopBtn = document.getElementById('stopSpeakingBtn');
    if (stopBtn) stopBtn.classList.add('d-none');
}
