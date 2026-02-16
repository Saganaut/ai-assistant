import { useState, useEffect } from 'react';
import styles from './Layout.module.css';
import { Chat } from '../Chat/Chat';
import { Dashboard } from '../Dashboard/Dashboard';

export function Layout() {
  const [showMobileChat, setShowMobileChat] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [apiStatus, setApiStatus] = useState<'connected' | 'disconnected'>('disconnected');

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch(
          `${window.location.protocol}//${window.location.hostname}:8000/api/health`
        );
        setApiStatus(res.ok ? 'connected' : 'disconnected');
      } catch {
        setApiStatus('disconnected');
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className={styles.layout}>
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <span className={styles.headerTitle}>AI Assistant</span>
        </div>
        <div className={styles.headerRight}>
          <span
            className={`${styles.headerStatus} ${
              apiStatus === 'connected' ? styles.statusConnected : styles.statusDisconnected
            }`}
          >
            {apiStatus === 'connected' ? '\u25CF Connected' : '\u25CB Disconnected'}
          </span>
          <button className={styles.settingsButton} onClick={() => setShowSettings(true)}>
            {'\u2699'}
          </button>
        </div>
      </header>

      <main className={styles.main}>
        <div className={styles.leftColumn}>
          <Dashboard />
        </div>
        <div className={showMobileChat ? styles.rightColumnVisible : styles.rightColumn}>
          <Chat />
        </div>
      </main>

      <button
        className={styles.floatingChatButton}
        onClick={() => setShowMobileChat(!showMobileChat)}
      >
        {showMobileChat ? '\u2715' : '\uD83D\uDCAC'}
      </button>

      {showSettings && (
        <div className={styles.settingsOverlay} onClick={() => setShowSettings(false)}>
          <div className={styles.settingsModal} onClick={(e) => e.stopPropagation()}>
            <div className={styles.settingsTitle}>Settings</div>

            <div className={styles.settingsSection}>
              <div className={styles.settingsSectionTitle}>Connection</div>
              <div className={styles.settingsRow}>
                <span>API Status</span>
                <span className={styles.settingsValue}>
                  {apiStatus === 'connected' ? 'Connected' : 'Disconnected'}
                </span>
              </div>
              <div className={styles.settingsRow}>
                <span>Backend URL</span>
                <span className={styles.settingsValue}>
                  {window.location.hostname}:8000
                </span>
              </div>
            </div>

            <div className={styles.settingsSection}>
              <div className={styles.settingsSectionTitle}>Configuration</div>
              <div className={styles.settingsRow}>
                <span>LLM Provider</span>
                <span className={styles.settingsValue}>Gemini</span>
              </div>
              <div className={styles.settingsRow}>
                <span>TTS Provider</span>
                <span className={styles.settingsValue}>ElevenLabs</span>
              </div>
              <div className={styles.settingsRow}>
                <span>STT</span>
                <span className={styles.settingsValue}>Whisper (local)</span>
              </div>
            </div>

            <div className={styles.settingsSection}>
              <div className={styles.settingsSectionTitle}>Info</div>
              <div className={styles.settingsRow}>
                <span>Version</span>
                <span className={styles.settingsValue}>0.7.0</span>
              </div>
              <div className={styles.settingsRow}>
                <span>API keys are configured server-side via environment variables.</span>
              </div>
            </div>

            <button className={styles.settingsClose} onClick={() => setShowSettings(false)}>
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
