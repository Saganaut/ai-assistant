import { API_BASE } from './api';

let currentAudio: HTMLAudioElement | null = null;

/**
 * Send text to the TTS endpoint and play the returned audio.
 * Returns a promise that resolves when playback finishes.
 */
export async function speakText(text: string): Promise<void> {
  stopSpeaking();

  const res = await fetch(`${API_BASE}/voice/tts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });

  if (!res.ok) {
    throw new Error(`TTS request failed: ${res.status}`);
  }

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const audio = new Audio(url);
  currentAudio = audio;

  return new Promise<void>((resolve) => {
    audio.onended = () => {
      URL.revokeObjectURL(url);
      currentAudio = null;
      resolve();
    };
    audio.onerror = () => {
      URL.revokeObjectURL(url);
      currentAudio = null;
      resolve();
    };
    audio.play().catch(() => {
      URL.revokeObjectURL(url);
      currentAudio = null;
      resolve();
    });
  });
}

/**
 * Stop any currently playing TTS audio.
 */
export function stopSpeaking(): void {
  if (currentAudio) {
    currentAudio.pause();
    currentAudio.src = '';
    currentAudio = null;
  }
}
