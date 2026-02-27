import { useState, useRef, useCallback, useMemo } from 'react';
import { error as logError } from '../../utils/logger';
import { getWsBase } from '../../services/api';
import styles from './VoiceButton.module.css';

interface VoiceButtonProps {
  onTranscription: (text: string) => void;
  disabled?: boolean;
}

const SpeechRecognitionCtor =
  typeof window !== 'undefined' && window.isSecureContext
    ? window.SpeechRecognition || window.webkitSpeechRecognition
    : undefined;

export function VoiceButton({ onTranscription, disabled }: VoiceButtonProps) {
  const [state, setState] = useState<'idle' | 'recording' | 'processing'>('idle');
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const useWebSpeech = useMemo(() => !!SpeechRecognitionCtor, []);

  // ── Web Speech API path (primary) ──

  const startWebSpeech = useCallback(() => {
    if (!SpeechRecognitionCtor) return;

    const recognition = new SpeechRecognitionCtor();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';
    recognitionRef.current = recognition;

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const transcript = event.results[0]?.[0]?.transcript;
      if (transcript) {
        onTranscription(transcript);
      }
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      if (event.error !== 'aborted') {
        logError('Speech recognition error:', event.error);
      }
      setState('idle');
    };

    recognition.onend = () => {
      setState('idle');
    };

    try {
      recognition.start();
      setState('recording');
    } catch (err) {
      logError('Speech recognition start failed:', err);
      setState('idle');
    }
  }, [onTranscription]);

  const stopWebSpeech = useCallback(() => {
    recognitionRef.current?.stop();
  }, []);

  // ── Whisper WebSocket path (fallback) ──

  const startWhisperRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });

        if (blob.size === 0) {
          setState('idle');
          return;
        }

        setState('processing');

        try {
          const ws = new WebSocket(`${getWsBase()}/voice/ws`);

          ws.onopen = () => {
            blob.arrayBuffer().then((buffer) => {
              ws.send(buffer);
            });
          };

          ws.onmessage = (event) => {
            try {
              const data = JSON.parse(event.data);
              if (data.type === 'transcription' && data.text) {
                onTranscription(data.text);
              }
            } catch {
              // ignore
            }
            ws.close();
            setState('idle');
          };

          ws.onerror = () => {
            setState('idle');
          };

          ws.onclose = () => {
            setState('idle');
          };

          // Timeout fallback
          setTimeout(() => {
            if (ws.readyState === WebSocket.OPEN) {
              ws.close();
            }
            setState('idle');
          }, 15000);
        } catch {
          setState('idle');
        }
      };

      mediaRecorder.start();
      setState('recording');
    } catch (err) {
      logError('Failed to start recording:', err);
      setState('idle');
    }
  }, [onTranscription]);

  const stopWhisperRecording = useCallback(() => {
    if (mediaRecorderRef.current && state === 'recording') {
      mediaRecorderRef.current.stop();
    }
  }, [state]);

  // ── Unified handlers ──

  const handleClick = () => {
    if (state === 'idle') {
      if (useWebSpeech) {
        startWebSpeech();
      } else {
        startWhisperRecording();
      }
    } else if (state === 'recording') {
      if (useWebSpeech) {
        stopWebSpeech();
      } else {
        stopWhisperRecording();
      }
    }
    // If processing, do nothing
  };

  const className =
    state === 'recording' ? styles.recording :
    state === 'processing' ? styles.processing :
    styles.voiceButton;

  const icon = state === 'recording' ? '\u23F9' : state === 'processing' ? '\u23F3' : '\uD83C\uDF99';

  const modeLabel = useWebSpeech ? 'Web Speech' : 'Whisper';
  const title =
    state === 'recording' ? 'Stop recording' :
    state === 'processing' ? 'Processing...' :
    `Push to talk (${modeLabel})`;

  return (
    <button
      className={className}
      onClick={handleClick}
      disabled={disabled || state === 'processing'}
      title={title}
    >
      {icon}
    </button>
  );
}
