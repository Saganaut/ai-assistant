import { useState, useRef, useCallback } from 'react';
import styles from './VoiceButton.module.css';

interface VoiceButtonProps {
  onTranscription: (text: string) => void;
  disabled?: boolean;
}

export function VoiceButton({ onTranscription, disabled }: VoiceButtonProps) {
  const [state, setState] = useState<'idle' | 'recording' | 'processing'>('idle');
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const startRecording = useCallback(async () => {
    if (disabled) return;

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
          const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
          const ws = new WebSocket(`${protocol}//${window.location.hostname}:8000/api/voice/ws`);

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
      console.error('Failed to start recording:', err);
      setState('idle');
    }
  }, [disabled, onTranscription]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && state === 'recording') {
      mediaRecorderRef.current.stop();
    }
  }, [state]);

  const handleClick = () => {
    if (state === 'idle') {
      startRecording();
    } else if (state === 'recording') {
      stopRecording();
    }
    // If processing, do nothing
  };

  const className =
    state === 'recording' ? styles.recording :
    state === 'processing' ? styles.processing :
    styles.voiceButton;

  const icon = state === 'recording' ? '\u23F9' : state === 'processing' ? '\u23F3' : '\uD83C\uDF99';

  return (
    <button
      className={className}
      onClick={handleClick}
      disabled={disabled || state === 'processing'}
      title={
        state === 'recording' ? 'Stop recording' :
        state === 'processing' ? 'Processing...' :
        'Push to talk'
      }
    >
      {icon}
    </button>
  );
}
