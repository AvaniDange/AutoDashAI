import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Send, User, Bot, Loader2, Mic, MicOff, Volume2, VolumeX, Languages, MessageSquareText, AudioLines, AlertTriangle } from 'lucide-react';

const SUGGESTION_CHIPS = [
    '📊 Show top categories',
    '📈 Show trends over time',
    '🥧 Change to pie chart',
    '🔍 Filter by region',
    '🔄 Reset dashboard',
    '🌙 Dark mode',
];

const VOICE_LANGUAGES = [
    { code: 'en-IN', label: 'English', geminiLabel: 'English', flag: '🌐' },
    { code: 'hi-IN', label: 'हिंदी', geminiLabel: 'Hindi', flag: '🇮🇳' },
    { code: 'mr-IN', label: 'मराठी', geminiLabel: 'Marathi', flag: '🇮🇳' },
    { code: 'gu-IN', label: 'ગુજરાતી', geminiLabel: 'Gujarati', flag: '🇮🇳' },
    { code: 'ta-IN', label: 'தமிழ்', geminiLabel: 'Tamil', flag: '🇮🇳' },
    { code: 'te-IN', label: 'తెలుగు', geminiLabel: 'Telugu', flag: '🇮🇳' },
    { code: 'kn-IN', label: 'ಕನ್ನಡ', geminiLabel: 'Kannada', flag: '🇮🇳' },
    { code: 'bn-IN', label: 'বাংলা', geminiLabel: 'Bengali', flag: '🇮🇳' },
    { code: 'pa-IN', label: 'ਪੰਜਾਬੀ', geminiLabel: 'Punjabi', flag: '🇮🇳' },
    { code: 'ml-IN', label: 'മലയാളം', geminiLabel: 'Malayalam', flag: '🇮🇳' },
    { code: 'or-IN', label: 'ଓଡ଼ିଆ', geminiLabel: 'Odia', flag: '🇮🇳' },
    { code: 'as-IN', label: 'অসমীয়া', geminiLabel: 'Assamese', flag: '🇮🇳' },
];

// Multilingual wake-word greetings
const WAKE_GREETINGS = {
    'en-IN': "Namaste! I'm Vidhur, your BI assistant. How can I help you today?",
    'hi-IN': "नमस्ते! मैं विधुर हूँ, आपका BI सहायक। आज मैं आपकी कैसे मदद कर सकता हूँ?",
    'mr-IN': "नमस्कार! मी विधुर आहे, तुमचा BI सहाय्यक. आज मी तुम्हाला कशी मदत करू शकतो?",
    'gu-IN': "નમસ્તે! હું વિધુર છું, તમારો BI સહાયક. આજે હું તમને કેવી રીતે મદદ કરી શકું?",
    'ta-IN': "வணக்கம்! நான் விதுர், உங்கள் BI உதவியாளர். இன்று நான் உங்களுக்கு எவ்வாறு உதவ முடியும்?",
    'te-IN': "నమస్తే! నేను విధుర్, మీ BI సహాయకుడు. ఈ రోజు నేను మీకు ఎలా సహాయం చేయగలను?",
    'kn-IN': "ನಮಸ್ಕಾರ! ನಾನು ವಿಧುರ್, ನಿಮ್ಮ BI ಸಹಾಯಕ. ಇಂದು ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಬಹುದು?",
    'bn-IN': "নমস্কার! আমি বিধুর, আপনার BI সহকারী। আজ আমি আপনাকে কীভাবে সাহায্য করতে পারি?",
    'pa-IN': "ਸਤ ਸ੍ਰੀ ਅਕਾਲ! ਮੈਂ ਵਿਧੁਰ ਹਾਂ, ਤੁਹਾਡਾ BI ਸਹਾਇਕ। ਅੱਜ ਮੈਂ ਤੁਹਾਡੀ ਕਿਵੇਂ ਮਦਦ ਕਰ ਸਕਦਾ ਹਾਂ?",
    'ml-IN': "നമസ്കാരം! ഞാൻ വിധുർ, നിങ്ങളുടെ BI അസിസ്റ്റന്റ്. ഇന്ന് ഞാൻ നിങ്ങളെ എങ്ങനെ സഹായിക്കാം?",
    'or-IN': "ନମସ୍କାର! ମୁଁ ବିଧୁର, ଆପଣଙ୍କ BI ସହାୟକ। ଆଜି ମୁଁ ଆପଣଙ୍କୁ କିପରି ସାହାଯ୍ୟ କରିପାରିବି?",
    'as-IN': "নমস্কাৰ! মই বিধুৰ, আপোনাৰ BI সহায়ক। আজি মই আপোনাক কেনেকৈ সহায় কৰিব পাৰোঁ?",
};

// Wake word phrases (multi-language)
const WAKE_PHRASES = [
    'hello vidhur', 'hello vidur', 'hey vidhur', 'hi vidhur',
    'ok vidhur', 'hello vidhur', 'hey vidhur',
    // Hindi
    'हेलो विधुर', 'हाय विधुर', 'नमस्ते विधुर',
    // Bengali / Assamese
    'হেলো বিধুর', 'হ্যালো বিধুর',
    // Odia
    'ହେଲୋ ବିଧୁର',
    // Tamil
    'ஹலோ விதுர்',
    // Telugu
    'హలో విధుర్',
    // Kannada
    'ಹಲೋ ವಿಧುರ್',
    // Gujarati
    'હેલો વિધુર',
    // Marathi
    'हॅलो विधुर',
    // Punjabi
    'ਹੈਲੋ ਵਿਧੁਰ',
    // Malayalam
    'ഹലോ വിധുർ',
];

// Exit phrases to end continuous conversation
const EXIT_PHRASES = [
    'goodbye vidhur', 'bye vidhur', 'thank you vidhur',
    'thanks vidhur', 'stop vidhur', 'stop listening',
    'अलविदा विधुर', 'धन्यवाद विधुर',
    'বিদায় বিধুর', 'ধন্যবাদ বিধুর',
];

// Check if browser supports SpeechRecognition
const SpeechRecognition = typeof window !== 'undefined'
    ? (window.SpeechRecognition || window.webkitSpeechRecognition)
    : null;

const ChatInterface = ({ messages, onSendMessage, loading, theme }) => {
    const isDark = theme === 'dark';
    const [input, setInput] = useState('');
    const messagesEndRef = useRef(null);

    // Voice state
    const [isListening, setIsListening] = useState(false);
    const [isWakeWordMode, setIsWakeWordMode] = useState(false);
    const [wakeWordActive, setWakeWordActive] = useState(false);
    const [responseMode, setResponseMode] = useState('voice'); // 'voice' | 'text'
    const [voiceLang, setVoiceLang] = useState(() => {
        try { return localStorage.getItem('vidhur_voice_lang') || 'en-IN'; }
        catch { return 'en-IN'; }
    });
    const [showLangPicker, setShowLangPicker] = useState(false);
    const [vidhurGreeted, setVidhurGreeted] = useState(false);
    const [detectedLang, setDetectedLang] = useState(null); // auto-detected language badge
    const [browserWarning, setBrowserWarning] = useState(false);
    const [voiceError, setVoiceError] = useState(null); // specific voice error message
    const [micPermission, setMicPermission] = useState('unknown'); // 'granted' | 'denied' | 'unknown'

    // Refs for mutable state (fixes stale closure bug)
    const recognitionRef = useRef(null);
    const wakeRecognitionRef = useRef(null);
    const synthRef = useRef(typeof window !== 'undefined' ? window.speechSynthesis : null);
    const isWakeWordModeRef = useRef(false);
    const wakeWordActiveRef = useRef(false);
    const isListeningRef = useRef(false);
    const continuousConvoRef = useRef(false); // continuous conversation after wake word
    const voiceLangRef = useRef(voiceLang);
    const responseModeRef = useRef(responseMode);
    const recognitionActiveRef = useRef(false); // guards against overlapping start/stop
    const wakeRetryCountRef = useRef(0); // for exponential backoff

    // Keep refs in sync with state
    useEffect(() => { isWakeWordModeRef.current = isWakeWordMode; }, [isWakeWordMode]);
    useEffect(() => { wakeWordActiveRef.current = wakeWordActive; }, [wakeWordActive]);
    useEffect(() => { isListeningRef.current = isListening; }, [isListening]);
    useEffect(() => { voiceLangRef.current = voiceLang; }, [voiceLang]);
    useEffect(() => { responseModeRef.current = responseMode; }, [responseMode]);

    // Persist language selection
    useEffect(() => {
        try { localStorage.setItem('vidhur_voice_lang', voiceLang); }
        catch { /* ignore */ }
    }, [voiceLang]);

    // Check browser compatibility on mount
    useEffect(() => {
        if (!SpeechRecognition) {
            setBrowserWarning(true);
        }
    }, []);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // ===== Microphone Permission Pre-Check =====
    const checkMicPermission = useCallback(async () => {
        try {
            // Explicitly request microphone access — this surfaces the permission dialog
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            // Release the stream immediately — we just needed the permission
            stream.getTracks().forEach(track => track.stop());
            setMicPermission('granted');
            setVoiceError(null);
            return true;
        } catch (err) {
            console.error('Microphone permission denied:', err);
            setMicPermission('denied');
            if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
                setVoiceError('Microphone access denied. Please allow microphone in browser settings (🔒 icon in address bar) and refresh.');
            } else if (err.name === 'NotFoundError') {
                setVoiceError('No microphone found. Please connect a microphone and try again.');
            } else {
                setVoiceError(`Microphone error: ${err.message}`);
            }
            return false;
        }
    }, []);

    // Speak bot responses aloud (only in voice mode)
    useEffect(() => {
        if (responseModeRef.current !== 'voice' || messages.length === 0) return;
        const lastMsg = messages[messages.length - 1];
        if (lastMsg.role === 'assistant' && lastMsg.content) {
            // Determine the speech language: use detected language if available, else selected
            const speechLang = lastMsg._detectedLangCode || voiceLangRef.current;
            speakText(lastMsg.content, speechLang);

            // If in continuous conversation mode, restart listening after speech ends
            if (continuousConvoRef.current) {
                const waitForSpeech = () => {
                    if (synthRef.current && !synthRef.current.speaking) {
                        setTimeout(() => {
                            if (continuousConvoRef.current) {
                                startActiveListening();
                            }
                        }, 500);
                    } else {
                        setTimeout(waitForSpeech, 300);
                    }
                };
                setTimeout(waitForSpeech, 500);
            }
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [messages]);

    const speakText = useCallback((text, langCode) => {
        if (!synthRef.current) return;
        synthRef.current.cancel();

        const utterance = new SpeechSynthesisUtterance(text);
        const targetLang = langCode || voiceLangRef.current;
        utterance.lang = targetLang;
        utterance.rate = 0.95;
        utterance.pitch = 1.0;

        // Fetch available voices and explicitly set the correct regional voice
        const voices = synthRef.current.getVoices();
        if (voices.length > 0) {
            // Priority 1: Exact locale match (e.g., 'hi-IN')
            let matchedVoice = voices.find(v => v.lang === targetLang);
            
            // Priority 2: Prefix match (e.g., matching 'hi' if 'hi-IN' is unavailable)
            if (!matchedVoice) {
                const prefix = targetLang.split('-')[0];
                matchedVoice = voices.find(v => v.lang.startsWith(prefix));
            }
            
            // Priority 3: Sometimes Chrome labels voices by name (e.g., "Google हिन्दी")
            // This is a fallback but prefix matching usually catches what we need.

            if (matchedVoice) {
                utterance.voice = matchedVoice;
            }
        }

        synthRef.current.speak(utterance);
    }, []);

    // ===== Auto-detect language from voice input =====
    const detectLanguageFromCode = useCallback((langCode) => {
        // Map the SpeechRecognition detected lang code to our VOICE_LANGUAGES
        if (!langCode) return null;
        const code = langCode.toLowerCase();
        // Try exact match first
        const exact = VOICE_LANGUAGES.find(l => l.code.toLowerCase() === code);
        if (exact) return exact;
        // Try prefix match (e.g., 'hi' matches 'hi-IN')
        const prefix = code.split('-')[0];
        return VOICE_LANGUAGES.find(l => l.code.toLowerCase().startsWith(prefix)) || null;
    }, []);

    // ===== Wake Word Detection ("Hello Vidhur") =====
    const startWakeWordListener = useCallback(() => {
        if (!SpeechRecognition) return;

        // Clean up any existing wake listener
        if (wakeRecognitionRef.current) {
            try { wakeRecognitionRef.current.stop(); } catch (e) { /* ignore */ }
            wakeRecognitionRef.current = null;
        }

        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = voiceLangRef.current;
        wakeRecognitionRef.current = recognition;

        recognition.onresult = (event) => {
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript.toLowerCase().trim();

                // Check for wake phrases
                const isWakeWord = WAKE_PHRASES.some(phrase => transcript.includes(phrase));

                if (isWakeWord) {
                    // Wake word detected!
                    wakeRetryCountRef.current = 0; // Reset retry count on success
                    setVidhurGreeted(true);
                    setWakeWordActive(true);
                    wakeWordActiveRef.current = true;
                    continuousConvoRef.current = true; // Enable continuous conversation

                    // Play greeting in selected language
                    const greeting = WAKE_GREETINGS[voiceLangRef.current] || WAKE_GREETINGS['en-IN'];
                    speakText(greeting, voiceLangRef.current);

                    // Stop wake word listener, start active listening after greeting
                    try { recognition.stop(); } catch (e) { /* ignore */ }

                    // Wait for greeting to finish, then start listening
                    const waitForGreeting = () => {
                        if (synthRef.current && !synthRef.current.speaking) {
                            setTimeout(() => {
                                startActiveListening();
                            }, 300);
                        } else {
                            setTimeout(waitForGreeting, 300);
                        }
                    };
                    setTimeout(waitForGreeting, 800);
                    return;
                }
            }
        };

        recognition.onerror = (e) => {
            if (e.error !== 'no-speech' && e.error !== 'aborted') {
                console.error('Wake word recognition error:', e.error);
            }
        };

        recognition.onend = () => {
            // Restart if still in wake word mode and not in active conversation
            if (isWakeWordModeRef.current && !wakeWordActiveRef.current && !isListeningRef.current) {
                // Exponential backoff for reconnection (300ms, 600ms, 1200ms, max 5000ms)
                const delay = Math.min(300 * Math.pow(2, wakeRetryCountRef.current), 5000);
                wakeRetryCountRef.current = Math.min(wakeRetryCountRef.current + 1, 5);

                setTimeout(() => {
                    if (isWakeWordModeRef.current && !wakeWordActiveRef.current && !isListeningRef.current) {
                        try {
                            if (wakeRecognitionRef.current) {
                                wakeRecognitionRef.current.start();
                                wakeRetryCountRef.current = 0; // Reset on successful start
                            }
                        } catch (e) {
                            // Create a new instance if the old one is dead
                            startWakeWordListener();
                        }
                    }
                }, delay);
            }
        };

        try {
            recognition.start();
            wakeRetryCountRef.current = 0;
        } catch (e) {
            console.error('Failed to start wake word listener:', e);
        }
    }, [speakText]);

    // Toggle wake word mode
    const toggleWakeWordMode = async () => {
        if (isWakeWordMode) {
            // Turning OFF
            setIsWakeWordMode(false);
            isWakeWordModeRef.current = false;
            setWakeWordActive(false);
            wakeWordActiveRef.current = false;
            continuousConvoRef.current = false;
            wakeRetryCountRef.current = 0;
            if (wakeRecognitionRef.current) {
                try { wakeRecognitionRef.current.stop(); } catch (e) { /* ignore */ }
                wakeRecognitionRef.current = null;
            }
            if (recognitionRef.current) {
                try { recognitionRef.current.stop(); } catch (e) { /* ignore */ }
            }
        } else {
            // Turning ON — check microphone permission first
            if (!SpeechRecognition) {
                setBrowserWarning(true);
                return;
            }
            const hasPermission = await checkMicPermission();
            if (!hasPermission) return;

            setIsWakeWordMode(true);
            isWakeWordModeRef.current = true;
            setVoiceError(null);
            startWakeWordListener();
        }
    };

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            if (wakeRecognitionRef.current) {
                try { wakeRecognitionRef.current.stop(); } catch (e) { /* ignore */ }
            }
            if (recognitionRef.current) {
                try { recognitionRef.current.stop(); } catch (e) { /* ignore */ }
            }
            continuousConvoRef.current = false;
        };
    }, []);

    // ===== Active Listening (for user command) =====
    const startActiveListening = useCallback(async () => {
        if (!SpeechRecognition) {
            setBrowserWarning(true);
            return;
        }

        // Prevent overlapping start/stop cycles
        if (recognitionActiveRef.current) {
            console.log('Recognition already active, skipping start');
            return;
        }

        // Stop any existing recognition cleanly
        if (recognitionRef.current) {
            try { recognitionRef.current.stop(); } catch (e) { /* ignore */ }
            recognitionRef.current = null;
        }

        recognitionActiveRef.current = true;

        // 250ms delay to let the previous instance fully close (increased from 150ms)
        setTimeout(() => {
            const recognition = new SpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = true;
            recognition.lang = voiceLangRef.current;
            recognitionRef.current = recognition;

            setIsListening(true);
            isListeningRef.current = true;
            setDetectedLang(null);
            setVoiceError(null);

            recognition.onresult = (event) => {
                let finalTranscript = '';
                let interimTranscript = '';

                for (let i = event.resultIndex; i < event.results.length; i++) {
                    if (event.results[i].isFinal) {
                        finalTranscript += event.results[i][0].transcript;
                    } else {
                        interimTranscript += event.results[i][0].transcript;
                    }
                }

                if (interimTranscript) {
                    setInput(interimTranscript);
                }

                if (finalTranscript) {
                    const trimmed = finalTranscript.trim().toLowerCase();

                    // Check for exit phrases (end continuous conversation)
                    const isExit = EXIT_PHRASES.some(phrase => trimmed.includes(phrase));
                    if (isExit && continuousConvoRef.current) {
                        continuousConvoRef.current = false;
                        setWakeWordActive(false);
                        wakeWordActiveRef.current = false;
                        setInput('');

                        // Say goodbye
                        const goodbyeMsg = {
                            'en-IN': "Goodbye! Say 'Hello Vidhur' whenever you need me again. 👋",
                            'hi-IN': "अलविदा! जब भी मेरी ज़रूरत हो 'हेलो विधुर' कहें। 👋",
                        };
                        speakText(
                            goodbyeMsg[voiceLangRef.current] || goodbyeMsg['en-IN'],
                            voiceLangRef.current
                        );

                        // Restart wake word listener
                        if (isWakeWordModeRef.current) {
                            setTimeout(() => startWakeWordListener(), 3000);
                        }
                        return;
                    }

                    setInput(finalTranscript);

                    // Auto-detect language from the recognition result
                    const detectedInfo = VOICE_LANGUAGES.find(l => l.code === voiceLangRef.current);
                    if (detectedInfo) {
                        setDetectedLang(detectedInfo);
                    }

                    // Auto-send after final result
                    setTimeout(() => {
                        if (finalTranscript.trim()) {
                            const selectedLang = detectedInfo?.geminiLabel || 'English';
                            onSendMessage(finalTranscript.trim(), selectedLang);
                            setInput('');
                        }
                    }, 300);
                }
            };

            recognition.onerror = (e) => {
                console.error('Speech recognition error:', e.error);
                setIsListening(false);
                isListeningRef.current = false;
                recognitionActiveRef.current = false;

                // Show specific, helpful error messages
                switch (e.error) {
                    case 'not-allowed':
                    case 'service-not-allowed':
                        setVoiceError('Microphone blocked. Click the 🔒 icon in your address bar → Allow microphone → Refresh page.');
                        setBrowserWarning(true);
                        break;
                    case 'no-speech':
                        setVoiceError('No speech detected. Please try again and speak clearly.');
                        // Auto-clear after 3 seconds
                        setTimeout(() => setVoiceError(null), 3000);
                        break;
                    case 'network':
                        setVoiceError('Network error. Speech recognition requires an internet connection.');
                        break;
                    case 'audio-capture':
                        setVoiceError('Microphone not found. Please connect a microphone.');
                        break;
                    default:
                        setVoiceError(`Voice error: ${e.error}. Try again.`);
                        setTimeout(() => setVoiceError(null), 5000);
                }
            };

            recognition.onend = () => {
                setIsListening(false);
                isListeningRef.current = false;
                recognitionActiveRef.current = false;
                setWakeWordActive(false);
                wakeWordActiveRef.current = false;

                // If in continuous mode and wake word mode is on, restart wake listener
                if (isWakeWordModeRef.current && !continuousConvoRef.current) {
                    setTimeout(() => {
                        startWakeWordListener();
                    }, 500);
                }
            };

            // Start recognition with retry logic
            const tryStart = (retryCount = 0) => {
                try {
                    recognition.start();
                } catch (e) {
                    console.error(`Failed to start listening (attempt ${retryCount + 1}):`, e);
                    if (retryCount < 1) {
                        // Retry once with a fresh instance after 500ms
                        setTimeout(() => {
                            recognitionRef.current = null;
                            recognitionActiveRef.current = false;
                            const freshRecognition = new SpeechRecognition();
                            freshRecognition.continuous = false;
                            freshRecognition.interimResults = true;
                            freshRecognition.lang = voiceLangRef.current;
                            freshRecognition.onresult = recognition.onresult;
                            freshRecognition.onerror = recognition.onerror;
                            freshRecognition.onend = recognition.onend;
                            recognitionRef.current = freshRecognition;
                            recognitionActiveRef.current = true;
                            try {
                                freshRecognition.start();
                            } catch (e2) {
                                console.error('Retry also failed:', e2);
                                setIsListening(false);
                                isListeningRef.current = false;
                                recognitionActiveRef.current = false;
                                setVoiceError('Voice recognition failed to start. Please try again.');
                            }
                        }, 500);
                    } else {
                        setIsListening(false);
                        isListeningRef.current = false;
                        recognitionActiveRef.current = false;
                        setVoiceError('Voice recognition failed to start. Please try again.');
                    }
                }
            };

            tryStart();
        }, 250); // 250ms delay to prevent InvalidStateError
    }, [onSendMessage, startWakeWordListener, speakText, checkMicPermission]);

    const toggleMic = async () => {
        if (isListening) {
            if (recognitionRef.current) {
                try { recognitionRef.current.stop(); } catch (e) { /* ignore */ }
            }
            setIsListening(false);
            isListeningRef.current = false;
            recognitionActiveRef.current = false;
            continuousConvoRef.current = false; // Stop continuous conversation on manual mic off
        } else {
            if (!SpeechRecognition) {
                setBrowserWarning(true);
                return;
            }
            // Check microphone permission first
            const hasPermission = await checkMicPermission();
            if (!hasPermission) return;

            startActiveListening();
        }
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        if (input.trim() && !loading) {
            const selectedLang = VOICE_LANGUAGES.find(l => l.code === voiceLang)?.geminiLabel || 'English';
            onSendMessage(input, selectedLang);
            setInput('');
        }
    };

    return (
        <div className={`flex flex-col h-full ${isDark ? 'bg-slate-900 shadow-none' : 'bg-white shadow-none'}`}>

            {/* Browser Compatibility Warning */}
            {browserWarning && (
                <div className={`mx-4 mt-3 p-3 rounded-xl flex items-center gap-2 text-xs font-bold ${isDark ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' : 'bg-amber-50 text-amber-700 border border-amber-200'}`}>
                    <AlertTriangle size={14} />
                    <span>Voice requires Chrome or Edge browser. <button onClick={() => setBrowserWarning(false)} className="underline ml-1">Dismiss</button></span>
                </div>
            )}

            {/* Voice Error Banner */}
            {voiceError && (
                <div className={`mx-4 mt-2 p-3 rounded-xl flex items-start gap-2 text-xs font-bold ${isDark ? 'bg-red-500/10 text-red-400 border border-red-500/20' : 'bg-red-50 text-red-600 border border-red-200'}`}>
                    <MicOff size={14} className="shrink-0 mt-0.5" />
                    <span className="flex-1">{voiceError}</span>
                    <button onClick={() => setVoiceError(null)} className="shrink-0 underline opacity-60 hover:opacity-100">✕</button>
                </div>
            )}

            {/* Header — Vidhur Branding */}
            <div className={`p-5 border-b flex items-center justify-between ${isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-gray-100'}`}>
                <div className="flex items-center gap-3">
                    {/* Vidhur Avatar — pulsing amber ring when wake word mode active */}
                    <div className={`w-10 h-10 rounded-2xl bg-gradient-to-tr from-violet-600 via-indigo-500 to-cyan-400 flex items-center justify-center text-white shadow-lg shadow-indigo-500/30 font-black text-lg ${isWakeWordMode && !isListening ? 'ring-2 ring-amber-400 ring-offset-2 animate-pulse' : ''} ${isDark && isWakeWordMode ? 'ring-offset-slate-900' : ''}`}>
                        V
                    </div>
                    <div>
                        <h3 className={`font-black text-sm ${isDark ? 'text-slate-100' : 'text-gray-800'}`}>Vidhur</h3>
                        <div className="flex items-center gap-1.5 mt-0.5">
                            <span className={`w-1.5 h-1.5 rounded-full ${isListening ? 'bg-red-500 animate-pulse shadow-[0_0_8px_rgba(239,68,68,0.6)]' : isWakeWordMode ? 'bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.5)]' : 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]'}`}></span>
                            <span className={`text-[10px] font-black uppercase tracking-widest ${isListening ? 'text-red-400' : isWakeWordMode ? 'text-amber-400' : 'text-emerald-500'}`}>
                                {isListening ? 'Listening...' : isWakeWordMode ? (continuousConvoRef.current && wakeWordActive ? 'Vidhur Active' : 'Say "Hello Vidhur"') : `${responseMode === 'voice' ? '🔊' : '💬'} ${VOICE_LANGUAGES.find(l => l.code === voiceLang)?.label || 'English'}`}
                            </span>
                        </div>
                    </div>
                </div>

                {/* Header Actions */}
                <div className="flex items-center gap-1.5">
                    {/* Detected Language Badge */}
                    {detectedLang && (
                        <div className={`flex items-center gap-1 px-2 py-1 rounded-lg text-[9px] font-black uppercase tracking-wider ${isDark ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20' : 'bg-cyan-50 text-cyan-700 border border-cyan-200'}`}>
                            🎯 {detectedLang.label}
                        </div>
                    )}

                    {/* Language Picker Toggle */}
                    <div className="relative">
                        <button
                            onClick={() => setShowLangPicker(!showLangPicker)}
                            className={`p-2 rounded-xl transition-all ${isDark ? 'hover:bg-slate-800 text-slate-400' : 'hover:bg-gray-100 text-gray-500'}`}
                            title="Voice Language"
                        >
                            <Languages size={16} />
                        </button>
                        {showLangPicker && (
                            <div className={`absolute right-0 top-full mt-2 w-52 rounded-2xl shadow-2xl border z-50 overflow-hidden max-h-80 overflow-y-auto ${isDark ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200'}`}>
                                {VOICE_LANGUAGES.map(lang => (
                                    <button
                                        key={lang.code}
                                        onClick={() => { setVoiceLang(lang.code); setShowLangPicker(false); }}
                                        className={`w-full px-4 py-2.5 text-left text-sm font-bold flex items-center gap-2 transition-all ${
                                            voiceLang === lang.code
                                                ? (isDark ? 'bg-indigo-600/20 text-indigo-300' : 'bg-indigo-50 text-indigo-700')
                                                : (isDark ? 'text-slate-300 hover:bg-slate-700' : 'text-gray-700 hover:bg-gray-50')
                                        }`}
                                    >
                                        <span>{lang.flag}</span>
                                        <span className="flex-1">{lang.label}</span>
                                        <span className={`text-[10px] ${isDark ? 'text-slate-500' : 'text-gray-400'}`}>{lang.geminiLabel}</span>
                                        {voiceLang === lang.code && <span className="text-xs">✓</span>}
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Response Mode Toggle: Voice Reply / Text Reply */}
                    <div className={`flex items-center rounded-xl overflow-hidden border ${isDark ? 'border-slate-700' : 'border-gray-200'}`}>
                        <button
                            onClick={() => setResponseMode('voice')}
                            className={`flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-black uppercase tracking-wider transition-all ${
                                responseMode === 'voice'
                                    ? 'bg-indigo-600 text-white'
                                    : (isDark ? 'bg-slate-800 text-slate-400 hover:text-slate-200' : 'bg-gray-50 text-gray-500 hover:text-gray-700')
                            }`}
                            title="Vidhur replies with voice"
                        >
                            <AudioLines size={12} />
                            Voice
                        </button>
                        <button
                            onClick={() => setResponseMode('text')}
                            className={`flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-black uppercase tracking-wider transition-all ${
                                responseMode === 'text'
                                    ? 'bg-indigo-600 text-white'
                                    : (isDark ? 'bg-slate-800 text-slate-400 hover:text-slate-200' : 'bg-gray-50 text-gray-500 hover:text-gray-700')
                            }`}
                            title="Vidhur replies with text only"
                        >
                            <MessageSquareText size={12} />
                            Text
                        </button>
                    </div>

                    {/* Wake Word Toggle */}
                    <button
                        onClick={toggleWakeWordMode}
                        className={`p-2 rounded-xl transition-all ${
                            isWakeWordMode
                                ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30 shadow-lg shadow-amber-500/10'
                                : (isDark ? 'hover:bg-slate-800 text-slate-500' : 'hover:bg-gray-100 text-gray-400')
                        }`}
                        title={isWakeWordMode ? 'Disable wake word & continuous conversation' : 'Enable "Hello Vidhur" wake word'}
                    >
                        {isWakeWordMode ? <Mic size={16} /> : <MicOff size={16} />}
                    </button>
                </div>
            </div>

            {/* Messages */}
            <div className={`flex-1 overflow-y-auto p-4 space-y-6 ${isDark ? 'bg-slate-950/20' : 'bg-gray-50/30'}`}>
                {messages.length === 0 && (
                    <div className="flex flex-col items-center justify-center h-full text-center px-6">
                        {/* Vidhur Welcome */}
                        <div className={`w-16 h-16 rounded-3xl bg-gradient-to-tr from-violet-600 via-indigo-500 to-cyan-400 flex items-center justify-center mb-5 shadow-lg shadow-indigo-500/25 ${isWakeWordMode ? 'ring-4 ring-amber-400/50 animate-pulse' : ''}`}>
                            <span className="text-white font-black text-2xl">V</span>
                        </div>
                        <p className={`font-black text-base mb-1 ${isDark ? 'text-slate-200' : 'text-gray-800'}`}>
                            {vidhurGreeted ? 'Namaste! Vidhur is ready 🙏' : 'Meet Vidhur'}
                        </p>
                        <p className={`text-xs ${isDark ? 'text-slate-500' : 'text-gray-500'} leading-relaxed max-w-[260px] mb-2`}>
                            Your AI-powered Business Intelligence advisor.
                        </p>
                        <div className={`text-[10px] px-3 py-1.5 rounded-full mb-5 font-bold ${isDark ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' : 'bg-amber-50 text-amber-600 border border-amber-200'}`}>
                            💡 Say <strong>"Hello Vidhur"</strong> to activate voice mode
                        </div>
                        <div className="flex flex-wrap gap-2 justify-center max-w-[320px]">
                            {SUGGESTION_CHIPS.map((chip, idx) => (
                                <button
                                    key={idx}
                                    onClick={() => onSendMessage(chip)}
                                    disabled={loading}
                                    className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all active:scale-95 border ${isDark
                                        ? 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700 hover:border-indigo-500/50'
                                        : 'bg-white border-gray-200 text-gray-600 hover:bg-indigo-50 hover:border-indigo-300 hover:text-indigo-700'
                                    }`}
                                >
                                    {chip}
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {messages.map((msg, idx) => (
                    <div
                        key={idx}
                        className={`flex gap-3 max-w-[92%] ${msg.role === 'user' ? 'ml-auto flex-row-reverse' : ''}`}
                    >
                        <div
                            className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 shadow-lg font-bold text-sm ${msg.role === 'user'
                                ? 'bg-indigo-600 text-white'
                                : 'bg-gradient-to-tr from-violet-600 to-cyan-400 text-white'
                                }`}
                        >
                            {msg.role === 'user' ? <User size={16} /> : 'V'}
                        </div>

                        <div
                            className={`p-4 rounded-2xl text-sm leading-relaxed font-medium shadow-sm ${msg.role === 'user'
                                ? 'bg-indigo-600 text-white rounded-tr-sm'
                                : (isDark ? 'bg-slate-800 text-slate-200 border border-slate-700 rounded-tl-sm' : 'bg-white text-gray-700 border border-gray-100 rounded-tl-sm')
                                }`}
                        >
                            {msg.content}
                        </div>
                    </div>
                ))}

                {/* Listening indicator */}
                {isListening && (
                    <div className="flex gap-3 max-w-[92%]">
                        <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-violet-600 to-cyan-400 text-white flex items-center justify-center shrink-0 shadow-lg font-bold text-sm">
                            V
                        </div>
                        <div className={`p-4 rounded-2xl text-sm font-medium flex items-center gap-3 ${isDark ? 'bg-slate-800 text-red-400 border border-red-500/20' : 'bg-red-50 text-red-600 border border-red-100'} rounded-tl-sm`}>
                            <div className="flex gap-1">
                                <span className="w-2 h-2 bg-red-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                                <span className="w-2 h-2 bg-red-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                                <span className="w-2 h-2 bg-red-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                            </div>
                            Vidhur is listening...
                            {continuousConvoRef.current && (
                                <span className={`text-[9px] px-1.5 py-0.5 rounded ${isDark ? 'bg-amber-500/10 text-amber-400' : 'bg-amber-50 text-amber-600'}`}>
                                    CONTINUOUS
                                </span>
                            )}
                        </div>
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className={`p-5 border-t ${isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-gray-100'}`}>
                <form onSubmit={handleSubmit} className="relative group flex gap-2">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder={isListening ? "Listening..." : "Ask Vidhur anything..."}
                        className={`flex-1 px-6 py-4 pr-12 rounded-2xl border transition-all outline-none text-sm font-bold shadow-inner ${isDark
                                ? 'bg-slate-800 border-slate-700 text-white placeholder:text-slate-500 focus:border-indigo-500/50'
                                : 'bg-gray-50 border-gray-200 text-gray-800 placeholder:text-gray-400 focus:bg-white focus:border-indigo-500/50'
                            }`}
                    />
                    {/* Mic Button */}
                    <button
                        type="button"
                        onClick={toggleMic}
                        className={`p-3.5 rounded-2xl transition-all duration-200 shrink-0 ${
                            isListening
                                ? 'bg-red-500 text-white shadow-xl shadow-red-500/30 animate-pulse'
                                : (isDark ? 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-indigo-400 border border-slate-700' : 'bg-gray-100 text-gray-500 hover:bg-indigo-50 hover:text-indigo-600 border border-gray-200')
                        }`}
                        title={isListening ? 'Stop listening' : 'Start voice input'}
                    >
                        {isListening ? <MicOff size={18} /> : <Mic size={18} />}
                    </button>
                    {/* Send Button */}
                    <button
                        type="submit"
                        disabled={!input.trim() || loading}
                        className={`p-3.5 rounded-2xl transition-all duration-200 shrink-0 ${input.trim()
                            ? 'bg-gradient-to-r from-violet-600 to-indigo-600 text-white hover:from-violet-500 hover:to-indigo-500 shadow-xl shadow-indigo-500/20 active:scale-95'
                            : (isDark ? 'bg-slate-800 text-slate-600 border border-slate-700' : 'bg-gray-100 text-gray-400 border border-gray-200')
                            }`}
                    >
                        {loading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
                    </button>
                </form>
                {/* Bottom bar: Wake word indicator */}
                <div className="text-center mt-3 flex items-center justify-center gap-2">
                    {isWakeWordMode && !isListening && (
                        <div className="flex items-center gap-1.5 mr-1">
                            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse"></span>
                            <span className={`text-[9px] font-black uppercase tracking-widest ${isDark ? 'text-amber-500' : 'text-amber-500'}`}>
                                Wake Active
                            </span>
                        </div>
                    )}
                    <div className="w-4 h-4 rounded-md bg-gradient-to-tr from-violet-600 to-cyan-400 flex items-center justify-center">
                        <span className="text-white text-[7px] font-black">V</span>
                    </div>
                    <p className={`text-[10px] font-bold uppercase tracking-widest ${isDark ? 'text-slate-600' : 'text-gray-400'}`}>Vidhur • Gemini-Powered AI Engine</p>
                </div>
            </div>
        </div>
    );
};

export default ChatInterface;
