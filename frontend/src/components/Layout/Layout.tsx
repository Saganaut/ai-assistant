import { useState, useEffect, useCallback, useSyncExternalStore } from 'react';
import styles from './Layout.module.css';
import { Chat } from '../Chat/Chat';
import { Dashboard } from '../Dashboard/Dashboard';
import { API_BASE, getIntegrationStatus } from '../../services/api';
import type { IntegrationStatus } from '../../services/api';
import { useMode } from '../../contexts/ModeContext';
import type { AppMode } from '../../contexts/ModeContext';
import { getEntries, clearEntries, subscribe } from '../../utils/errorLog';
import type { ErrorEntry } from '../../utils/errorLog';

type ChatSize = 'half' | 'quarter' | 'collapsed';

function loadChatSize(): ChatSize {
  const saved = localStorage.getItem('chat_size');
  if (saved === 'half' || saved === 'quarter' || saved === 'collapsed') return saved;
  return 'half';
}

function loadDebugMode(): boolean {
  return localStorage.getItem('debug_mode') === 'true';
}

const MAIN_CLASS: Record<ChatSize, string> = {
  half: styles.mainHalf,
  quarter: styles.mainQuarter,
  collapsed: styles.mainCollapsed,
};

const MODE_LABELS: Record<AppMode, string> = {
  overview: 'Overview',
  health: 'Health',
  work: 'Work',
};

function formatTime(ts: number): string {
  return new Date(ts).toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

function entryTypeClass(type: ErrorEntry['type']): string {
  if (type === 'console') return styles.errorEntryConsole;
  if (type === 'unhandled') return styles.errorEntryUnhandled;
  return styles.errorEntryApi;
}

export function Layout() {
  const [showMobileChat, setShowMobileChat] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showErrors, setShowErrors] = useState(false);
  const [apiStatus, setApiStatus] = useState<'connected' | 'disconnected'>('disconnected');
  const [integrations, setIntegrations] = useState<IntegrationStatus | null>(null);
  const [chatSize, setChatSize] = useState<ChatSize>(loadChatSize);
  const [debugMode, setDebugMode] = useState<boolean>(loadDebugMode);
  const { mode, setMode } = useMode();

  // Subscribe to error log updates so badge re-renders.
  // getEntries() returns a stable reference between mutations — required by useSyncExternalStore.
  const errorEntries = useSyncExternalStore(subscribe, getEntries, getEntries);

  const updateChatSize = (size: ChatSize) => {
    setChatSize(size);
    localStorage.setItem('chat_size', size);
  };

  const toggleDebugMode = (val: boolean) => {
    setDebugMode(val);
    localStorage.setItem('debug_mode', String(val));
  };

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch(`${API_BASE}/health`);
        setApiStatus(res.ok ? 'connected' : 'disconnected');
      } catch {
        setApiStatus('disconnected');
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchIntegrations = useCallback(async () => {
    try {
      const status = await getIntegrationStatus();
      setIntegrations(status);
    } catch {
      setIntegrations(null);
    }
  }, []);

  useEffect(() => {
    if (showSettings) fetchIntegrations();
  }, [showSettings, fetchIntegrations]);

  useEffect(() => {
    fetchIntegrations();
  }, [fetchIntegrations]);

  return (
    <div className={styles.layout}>
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <span className={styles.headerTitle}>
            AI Assistant
            {mode !== 'overview' && (
              <span className={styles.modeLabel}>· {MODE_LABELS[mode]}</span>
            )}
          </span>
        </div>
        <div className={styles.headerRight}>
          {chatSize === 'collapsed' && (
            <button
              className={styles.chatOpenBtn}
              onClick={() => updateChatSize('half')}
            >
              Chat ›
            </button>
          )}
          <span
            className={`${styles.headerStatus} ${
              apiStatus === 'connected' ? styles.statusConnected : styles.statusDisconnected
            }`}
          >
            {apiStatus === 'connected' ? '\u25CF Connected' : '\u25CB Disconnected'}
          </span>

          {/* Error log button — visible only when debug mode is on */}
          {debugMode && (
            <button
              className={`${styles.errorLogBtn} ${
                errorEntries.length > 0 ? styles.errorLogBtnHasErrors : ''
              }`}
              onClick={() => setShowErrors(true)}
              title="View error log"
            >
              Errors
              {errorEntries.length > 0 && (
                <span className={styles.errorBadge}>
                  {errorEntries.length > 99 ? '99+' : errorEntries.length}
                </span>
              )}
            </button>
          )}

          {integrations && (
            <span className={styles.integrationDots}>
              <span
                className={`${styles.integrationDot} ${
                  integrations.google.connected ? styles.dotConnected : styles.dotDisconnected
                }`}
                title={`Google: ${integrations.google.connected ? 'Connected' : integrations.google.configured ? 'Not connected' : 'Not configured'}`}
              />
              <span
                className={`${styles.integrationDot} ${
                  integrations.github.connected ? styles.dotConnected : styles.dotDisconnected
                }`}
                title={`GitHub: ${integrations.github.connected ? 'Connected' : integrations.github.configured ? 'Not connected' : 'Not configured'}`}
              />
              <span
                className={`${styles.integrationDot} ${
                  integrations.wordpress.connected ? styles.dotConnected : styles.dotDisconnected
                }`}
                title={`WordPress: ${integrations.wordpress.connected ? 'Connected' : integrations.wordpress.configured ? 'Not connected' : 'Not configured'}`}
              />
            </span>
          )}
          <button className={styles.settingsButton} onClick={() => setShowSettings(true)}>
            {'\u2699'}
          </button>
        </div>
      </header>

      <main className={`${styles.main} ${MAIN_CLASS[chatSize]}`}>
        <div className={styles.leftColumn}>
          <Dashboard mode={mode} />
        </div>
        {chatSize !== 'collapsed' && (
          <div className={showMobileChat ? styles.rightColumnVisible : styles.rightColumn}>
            <div className={styles.chatResizeBar}>
              <button
                className={`${styles.chatSizeBtn} ${chatSize === 'collapsed' ? styles.chatSizeBtnActive : ''}`}
                onClick={() => updateChatSize('collapsed')}
                title="Collapse chat"
              >
                ◁
              </button>
              <button
                className={`${styles.chatSizeBtn} ${chatSize === 'quarter' ? styles.chatSizeBtnActive : ''}`}
                onClick={() => updateChatSize('quarter')}
                title="Quarter width"
              >
                ¼
              </button>
              <button
                className={`${styles.chatSizeBtn} ${chatSize === 'half' ? styles.chatSizeBtnActive : ''}`}
                onClick={() => updateChatSize('half')}
                title="Half width"
              >
                ½
              </button>
            </div>
            <Chat />
          </div>
        )}
      </main>

      <button
        className={styles.floatingChatButton}
        onClick={() => setShowMobileChat(!showMobileChat)}
      >
        {showMobileChat ? '\u2715' : '\uD83D\uDCAC'}
      </button>

      {/* ── Settings modal ── */}
      {showSettings && (
        <div className={styles.settingsOverlay} onClick={() => setShowSettings(false)}>
          <div className={styles.settingsModal} onClick={(e) => e.stopPropagation()}>
            <div className={styles.settingsTitle}>Settings</div>

            <div className={styles.settingsSection}>
              <div className={styles.settingsSectionTitle}>Mode</div>
              <div className={styles.modeSelector}>
                {(['overview', 'health', 'work'] as AppMode[]).map((m) => (
                  <button
                    key={m}
                    className={`${styles.modeSelectorBtn} ${mode === m ? styles.modeSelectorBtnActive : ''}`}
                    onClick={() => setMode(m)}
                  >
                    {MODE_LABELS[m]}
                  </button>
                ))}
              </div>
            </div>

            <div className={styles.settingsSection}>
              <div className={styles.settingsSectionTitle}>Developer</div>
              <div className={styles.settingsRow}>
                <span>Debug mode</span>
                <button
                  className={`${styles.modeSelectorBtn} ${debugMode ? styles.modeSelectorBtnActive : ''}`}
                  style={{ padding: '2px 12px', fontSize: '0.8rem' }}
                  onClick={() => toggleDebugMode(!debugMode)}
                >
                  {debugMode ? 'On' : 'Off'}
                </button>
              </div>
              <div className={styles.settingsRow} style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>
                <span>Shows error log button in header. Captures console errors and unhandled rejections.</span>
              </div>
            </div>

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
                <span className={styles.settingsValue}>{API_BASE}</span>
              </div>
            </div>

            <div className={styles.settingsSection}>
              <div className={styles.settingsSectionTitle}>Integrations</div>
              {integrations ? (
                <>
                  <div className={styles.settingsRow}>
                    <span>Google Calendar</span>
                    <span className={`${styles.settingsStatus} ${integrations.google.connected ? styles.settingsStatusOn : styles.settingsStatusOff}`}>
                      {integrations.google.connected ? 'Connected' : integrations.google.configured ? 'Not connected' : 'Not configured'}
                    </span>
                  </div>
                  <div className={styles.settingsRow}>
                    <span>Google Drive</span>
                    <span className={`${styles.settingsStatus} ${integrations.google.connected ? styles.settingsStatusOn : styles.settingsStatusOff}`}>
                      {integrations.google.connected ? 'Connected' : integrations.google.configured ? 'Not connected' : 'Not configured'}
                    </span>
                  </div>
                  <div className={styles.settingsRow}>
                    <span>Gmail</span>
                    <span className={`${styles.settingsStatus} ${integrations.google.connected ? styles.settingsStatusOn : styles.settingsStatusOff}`}>
                      {integrations.google.connected ? 'Connected' : integrations.google.configured ? 'Not connected' : 'Not configured'}
                    </span>
                  </div>
                  <div className={styles.settingsRow}>
                    <span>GitHub</span>
                    <span className={`${styles.settingsStatus} ${integrations.github.connected ? styles.settingsStatusOn : styles.settingsStatusOff}`}>
                      {integrations.github.connected ? 'Connected' : integrations.github.configured ? 'Not connected' : 'Not configured'}
                    </span>
                  </div>
                  <div className={styles.settingsRow}>
                    <span>WordPress</span>
                    <span className={`${styles.settingsStatus} ${integrations.wordpress.connected ? styles.settingsStatusOn : styles.settingsStatusOff}`}>
                      {integrations.wordpress.connected ? 'Connected' : integrations.wordpress.configured ? 'Not connected' : 'Not configured'}
                    </span>
                  </div>
                </>
              ) : (
                <div className={styles.settingsRow}>
                  <span>Loading...</span>
                </div>
              )}
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
                <span className={styles.settingsValue}>0.8.0</span>
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

      {/* ── Error log modal ── */}
      {showErrors && (
        <div className={styles.errorModalOverlay} onClick={() => setShowErrors(false)}>
          <div className={styles.errorModal} onClick={(e) => e.stopPropagation()}>
            <div className={styles.errorModalHeader}>
              <span className={styles.errorModalTitle}>
                Error Log
                {errorEntries.length > 0 && ` (${errorEntries.length})`}
              </span>
              <div className={styles.errorModalActions}>
                {errorEntries.length > 0 && (
                  <button className={styles.errorClearBtn} onClick={clearEntries}>
                    Clear all
                  </button>
                )}
                <button className={styles.settingsButton} onClick={() => setShowErrors(false)}>
                  ×
                </button>
              </div>
            </div>

            <div className={styles.errorList}>
              {errorEntries.length === 0 ? (
                <div className={styles.errorEmpty}>No errors captured.</div>
              ) : (
                [...errorEntries].reverse().map((entry) => (
                  <div
                    key={entry.id}
                    className={`${styles.errorEntry} ${entryTypeClass(entry.type)}`}
                  >
                    <div className={styles.errorEntryHeader}>
                      <span className={styles.errorEntryType}>{entry.type}</span>
                      <span className={styles.errorEntryTime}>{formatTime(entry.ts)}</span>
                    </div>
                    <div className={styles.errorEntryMessage}>{entry.message}</div>
                    {entry.detail && (
                      <div className={styles.errorEntryDetail}>{entry.detail}</div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
