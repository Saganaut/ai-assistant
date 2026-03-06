import { useState, useRef, useEffect, useCallback } from 'react';
import { Terminal } from 'xterm';
import { FitAddon } from '@xterm/addon-fit';
import 'xterm/css/xterm.css';
import {
  listConversations,
  getConversation,
  deleteConversation,
  getWsBase,
  type ConversationSummary,
} from '../../services/api';
import { VoiceButton } from './VoiceButton';
import { speakText, stopSpeaking } from '../../services/tts';
import { log, warn, error as logError } from '../../utils/logger';
import styles from './Chat.module.css';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

type CliMode = 'claude' | 'gemini';

const CLI_LABELS: Record<CliMode, string> = {
  claude: 'Claude CLI',
  gemini: 'Gemini CLI',
};

export function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [showSidebar, setShowSidebar] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [cliMode, setCliMode] = useState<CliMode | null>(null);
  const [ttsEnabled, setTtsEnabled] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);

  // Refs — stable across renders, no re-render on change
  const ttsEnabledRef = useRef(false);
  const messagesRef = useRef<Message[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<Terminal | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const cliWsRef = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttempts = useRef(0);
  const unmountedRef = useRef(false);

  // CLI-specific refs
  const cliModeRef = useRef<CliMode | null>(null);
  const cliSessionIdRef = useRef<string | null>(null);
  const cliIntentionalCloseRef = useRef(false);
  const cliReconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const cliReconnectAttemptsRef = useRef(0);

  useEffect(() => { ttsEnabledRef.current = ttsEnabled; }, [ttsEnabled]);
  useEffect(() => { messagesRef.current = messages; }, [messages]);

  const handleTtsToggle = useCallback(() => {
    setTtsEnabled((prev) => {
      if (prev) stopSpeaking();
      return !prev;
    });
    setIsSpeaking(false);
  }, []);

  const loadConversations = useCallback(async () => {
    try {
      const convs = await listConversations();
      setConversations(convs);
    } catch { /* API might not be up yet */ }
  }, []);

  useEffect(() => { loadConversations(); }, [loadConversations]);

  // ── Chat WebSocket ──────────────────────────────────────────────────────────

  const connectWebSocket = useCallback(() => {
    if (unmountedRef.current) return;
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.close();
    }

    const ws = new WebSocket(`${getWsBase()}/chat/ws`);
    wsRef.current = ws;

    ws.onopen = () => {
      log('[WS] Connected');
      reconnectAttempts.current = 0;
      setWsConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'end') {
          setIsStreaming(false);
          if (data.conversation_id) {
            setConversationId(data.conversation_id);
            loadConversations();
          }
          if (ttsEnabledRef.current) {
            const last = messagesRef.current[messagesRef.current.length - 1];
            if (last?.role === 'assistant' && last.content) {
              setIsSpeaking(true);
              speakText(last.content).finally(() => setIsSpeaking(false));
            }
          }
          return;
        }
      } catch {
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last?.role === 'assistant') {
            return [...prev.slice(0, -1), { ...last, content: last.content + event.data }];
          }
          return [...prev, { role: 'assistant', content: event.data }];
        });
      }
    };

    ws.onclose = () => {
      setIsStreaming(false);
      setWsConnected(false);
      if (unmountedRef.current) return;
      const delay = Math.min(1000 * 2 ** reconnectAttempts.current, 30000);
      reconnectAttempts.current += 1;
      warn(`[WS] Disconnected, reconnecting in ${delay}ms`);
      reconnectTimeout.current = setTimeout(connectWebSocket, delay);
    };

    ws.onerror = (e) => { logError('[WS] Error:', e); };
  }, [loadConversations]);

  useEffect(() => {
    unmountedRef.current = false;
    connectWebSocket();
    return () => {
      unmountedRef.current = true;
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
      if (wsRef.current) { wsRef.current.onclose = null; wsRef.current.close(); }
    };
  }, [connectWebSocket]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // ── CLI mode ────────────────────────────────────────────────────────────────

  const exitCliMode = useCallback(() => {
    cliIntentionalCloseRef.current = true;
    if (cliReconnectTimeoutRef.current) {
      clearTimeout(cliReconnectTimeoutRef.current);
      cliReconnectTimeoutRef.current = null;
    }
    if (cliWsRef.current) {
      cliWsRef.current.onclose = null;
      cliWsRef.current.close();
      cliWsRef.current = null;
    }
    cliSessionIdRef.current = null;
    cliModeRef.current = null;
    cliReconnectAttemptsRef.current = 0;
    setCliMode(null);
  }, []);

  /**
   * Open (or re-open) the CLI WebSocket.  Pass sessionId to resume a
   * live backend PTY session.  The xterm Terminal must already exist.
   */
  const connectCliWs = useCallback(
    (mode: CliMode, sessionId: string | null) => {
      if (cliWsRef.current) {
        cliWsRef.current.onclose = null;
        cliWsRef.current.close();
      }

      const url = sessionId
        ? `${getWsBase()}/chat/${mode}?session_id=${encodeURIComponent(sessionId)}`
        : `${getWsBase()}/chat/${mode}`;

      const ws = new WebSocket(url);
      cliWsRef.current = ws;

      ws.onopen = () => {
        log(`[${CLI_LABELS[mode]}] WS connected`);
        cliReconnectAttemptsRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);

          if (msg.type === 'cli_ready') {
            cliSessionIdRef.current = msg.session_id;
            if (msg.resumed) {
              xtermRef.current?.write('\r\n\x1b[33m[Reconnected to session]\x1b[0m\r\n');
            }
            // Send actual terminal dimensions now that we know them
            if (xtermRef.current) {
              ws.send(JSON.stringify({
                type: 'resize',
                cols: xtermRef.current.cols,
                rows: xtermRef.current.rows,
              }));
            }
            return;
          }

          if (msg.type === 'cli_exit') {
            xtermRef.current?.write(
              `\r\n\x1b[90m[Process exited with code ${msg.code}]\x1b[0m\r\n`
            );
            cliSessionIdRef.current = null;
            // Delay so the user can read the exit message
            setTimeout(exitCliMode, 1500);
            return;
          }
        } catch {
          // Raw PTY output — write directly to xterm
          xtermRef.current?.write(event.data);
        }
      };

      ws.onclose = () => {
        log(`[${CLI_LABELS[mode]}] WS closed`);
        if (cliIntentionalCloseRef.current) return;
        if (!cliModeRef.current) return; // already exited

        const delay = Math.min(1000 * 2 ** cliReconnectAttemptsRef.current, 15000);
        cliReconnectAttemptsRef.current++;
        const secs = Math.round(delay / 1000);
        xtermRef.current?.write(
          `\r\n\x1b[33m[Disconnected. Reconnecting in ${secs}s...]\x1b[0m\r\n`
        );

        cliReconnectTimeoutRef.current = setTimeout(() => {
          if (!cliModeRef.current || cliIntentionalCloseRef.current) return;
          connectCliWs(mode, cliSessionIdRef.current);
        }, delay);
      };

      ws.onerror = (e) => { logError(`[${CLI_LABELS[mode]}] Error:`, e); };
    },
    [exitCliMode]
  );

  // Initialize xterm when entering CLI mode
  useEffect(() => {
    if (!cliMode || !terminalRef.current) return;

    cliModeRef.current = cliMode;
    cliIntentionalCloseRef.current = false;
    cliReconnectAttemptsRef.current = 0;
    cliSessionIdRef.current = null;

    const term = new Terminal({
      cursorBlink: true,
      fontSize: 13,
      fontFamily: "'Fira Code', 'Cascadia Code', 'Consolas', monospace",
      theme: {
        background: '#0d0d0d',
        foreground: '#e0e0e0',
        cursor: '#e0e0e0',
        selectionBackground: '#444',
      },
      scrollback: 5000,
      allowTransparency: false,
      // Don't convert \n → \r\n: the PTY already sends \r\n
      convertEol: false,
    });

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(terminalRef.current);

    xtermRef.current = term;
    fitAddonRef.current = fitAddon;

    // Forward keystrokes to the CLI process
    term.onData((data) => {
      if (cliWsRef.current?.readyState === WebSocket.OPEN) {
        cliWsRef.current.send(data);
      }
    });

    // Notify backend whenever xterm resizes
    term.onResize(({ cols, rows }) => {
      if (cliWsRef.current?.readyState === WebSocket.OPEN) {
        cliWsRef.current.send(JSON.stringify({ type: 'resize', cols, rows }));
      }
    });

    const handleWindowResize = () => fitAddonRef.current?.fit();
    window.addEventListener('resize', handleWindowResize);

    // Use rAF to ensure the container is fully laid out before fitting,
    // then connect — so the first resize message has correct dimensions.
    const rafId = requestAnimationFrame(() => {
      fitAddon.fit();
      term.focus();
      connectCliWs(cliMode, null);
    });

    return () => {
      cancelAnimationFrame(rafId);
      window.removeEventListener('resize', handleWindowResize);
      if (cliReconnectTimeoutRef.current) {
        clearTimeout(cliReconnectTimeoutRef.current);
        cliReconnectTimeoutRef.current = null;
      }
      if (cliWsRef.current) {
        cliWsRef.current.onclose = null;
        cliWsRef.current.close();
        cliWsRef.current = null;
      }
      term.dispose();
      xtermRef.current = null;
      fitAddonRef.current = null;
      cliModeRef.current = null;
    };
  }, [cliMode, connectCliWs]);

  // ── Regular chat ────────────────────────────────────────────────────────────

  const sendMessage = () => {
    if (!input.trim() || isStreaming) return;
    const trimmed = input.trim();

    if (trimmed === '/clear') { setInput(''); startNewConversation(); return; }

    if (trimmed === '/claude' || trimmed === '/gemini') {
      setInput('');
      setCliMode(trimmed.slice(1) as CliMode);
      return;
    }

    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      connectWebSocket();
      return;
    }

    const userMessage: Message = { role: 'user', content: trimmed };
    setMessages((prev) => [...prev, userMessage]);
    const payload = conversationId
      ? JSON.stringify({ content: trimmed, conversation_id: conversationId })
      : trimmed;
    wsRef.current.send(payload);
    setInput('');
    setIsStreaming(true);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  };

  const loadConversation = async (id: number) => {
    try {
      const conv = await getConversation(id);
      setMessages(conv.messages.map((m) => ({ role: m.role as 'user' | 'assistant', content: m.content })));
      setConversationId(id);
      setShowSidebar(false);
    } catch { /* ignore */ }
  };

  const handleDeleteConversation = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    await deleteConversation(id);
    if (conversationId === id) { setMessages([]); setConversationId(null); }
    loadConversations();
  };

  const startNewConversation = () => {
    setMessages([]);
    setConversationId(null);
    setShowSidebar(false);
  };

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className={styles.chat}>
      <div className={styles.chatHeader}>
        <button className={styles.sidebarToggle} onClick={() => setShowSidebar(!showSidebar)}>
          {showSidebar ? '\u2715' : '\u2630'}
        </button>
        <span className={styles.chatTitle}>
          {cliMode ? (
            <>{CLI_LABELS[cliMode]}<span className={styles.claudeIndicator}>LIVE</span></>
          ) : (
            conversationId ? `Chat #${conversationId}` : 'New Chat'
          )}
          {!wsConnected && !cliMode && (
            <span className={styles.disconnected}> (reconnecting...)</span>
          )}
        </span>
        {!cliMode && (
          <button
            className={`${styles.ttsToggle} ${ttsEnabled ? styles.ttsToggleActive : ''}`}
            onClick={handleTtsToggle}
            title={ttsEnabled ? (isSpeaking ? 'Speaking...' : 'Read aloud ON') : 'Read aloud'}
          >
            {isSpeaking ? '\uD83D\uDD0A' : '\uD83D\uDD08'}
          </button>
        )}
        {cliMode ? (
          <button className={styles.newChatButton} onClick={exitCliMode}>Exit</button>
        ) : (
          <button className={styles.newChatButton} onClick={startNewConversation}>+</button>
        )}
      </div>

      {showSidebar && !cliMode && (
        <div className={styles.sidebar}>
          <div className={styles.sidebarTitle}>Conversations</div>
          {conversations.length === 0 ? (
            <div className={styles.sidebarEmpty}>No conversations yet</div>
          ) : (
            conversations.map((conv) => (
              <div
                key={conv.id}
                className={`${styles.sidebarItem} ${conv.id === conversationId ? styles.sidebarItemActive : ''}`}
                onClick={() => loadConversation(conv.id)}
              >
                <span className={styles.sidebarItemTitle}>{conv.title}</span>
                <button
                  className={styles.sidebarItemDelete}
                  onClick={(e) => handleDeleteConversation(conv.id, e)}
                >
                  {'\u2715'}
                </button>
              </div>
            ))
          )}
        </div>
      )}

      {cliMode ? (
        <div className={styles.terminalOutput} ref={terminalRef} />
      ) : (
        <>
          <div className={styles.messages}>
            {messages.length === 0 && (
              <div className={styles.empty}>Send a message to start chatting</div>
            )}
            {messages.map((msg, i) => (
              <div
                key={i}
                className={msg.role === 'user' ? styles.messageUser : styles.messageAssistant}
              >
                {msg.content}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
          <div className={styles.inputArea}>
            <textarea
              className={styles.input}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type a message or /claude…"
              rows={1}
              disabled={isStreaming}
            />
            <VoiceButton
              onTranscription={(text) => setInput((prev) => prev ? `${prev} ${text}` : text)}
              disabled={isStreaming}
            />
            <button
              className={styles.sendButton}
              onClick={sendMessage}
              disabled={isStreaming || !input.trim()}
            >
              Send
            </button>
          </div>
        </>
      )}
    </div>
  );
}
