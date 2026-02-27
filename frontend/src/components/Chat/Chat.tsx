import { useState, useRef, useEffect, useCallback } from 'react';
import { Terminal } from 'xterm';
import { FitAddon } from '@xterm/addon-fit';
import 'xterm/css/xterm.css';
import { listConversations, getConversation, deleteConversation, getWsBase, type ConversationSummary } from '../../services/api';
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

  // Keep refs in sync so WS callback can read current values
  useEffect(() => {
    ttsEnabledRef.current = ttsEnabled;
  }, [ttsEnabled]);

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

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
    } catch {
      // API might not be up yet
    }
  }, []);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  const connectWebSocket = useCallback(() => {
    if (unmountedRef.current) return;

    // Close existing connection if any
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
          // Read aloud if TTS is enabled
          if (ttsEnabledRef.current) {
            const last = messagesRef.current[messagesRef.current.length - 1];
            if (last && last.role === 'assistant' && last.content) {
              setIsSpeaking(true);
              speakText(last.content).finally(() => setIsSpeaking(false));
            }
          }
          return;
        }
      } catch {
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last && last.role === 'assistant') {
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

      // Exponential backoff: 1s, 2s, 4s, 8s, max 30s
      const delay = Math.min(1000 * 2 ** reconnectAttempts.current, 30000);
      reconnectAttempts.current += 1;
      warn(`[WS] Disconnected, reconnecting in ${delay}ms (attempt ${reconnectAttempts.current})`);
      reconnectTimeout.current = setTimeout(connectWebSocket, delay);
    };

    ws.onerror = (e) => {
      logError('[WS] Error:', e);
    };
  }, [loadConversations]);

  useEffect(() => {
    unmountedRef.current = false;
    connectWebSocket();

    return () => {
      unmountedRef.current = true;
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
      if (cliWsRef.current) {
        cliWsRef.current.onclose = null;
        cliWsRef.current.close();
      }
    };
  }, [connectWebSocket]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const exitCliMode = useCallback(() => {
    if (cliWsRef.current) {
      cliWsRef.current.onclose = null;
      cliWsRef.current.close();
      cliWsRef.current = null;
    }
    if (xtermRef.current) {
      xtermRef.current.dispose();
      xtermRef.current = null;
    }
    fitAddonRef.current = null;
    setCliMode(null);
  }, []);

  // Initialize xterm.js when entering CLI mode
  useEffect(() => {
    if (!cliMode || !terminalRef.current) return;

    const label = CLI_LABELS[cliMode];

    const term = new Terminal({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: "'Fira Code', 'Cascadia Code', 'Consolas', monospace",
      theme: {
        background: '#0d0d0d',
        foreground: '#e0e0e0',
        cursor: '#e0e0e0',
      },
      convertEol: true,
    });
    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(terminalRef.current);
    fitAddon.fit();

    xtermRef.current = term;
    fitAddonRef.current = fitAddon;

    // Handle window resize
    const handleResize = () => fitAddon.fit();
    window.addEventListener('resize', handleResize);

    // Connect to CLI WebSocket
    const ws = new WebSocket(`${getWsBase()}/chat/${cliMode}`);
    cliWsRef.current = ws;

    ws.onopen = () => {
      log(`[${label}] WebSocket connected`);
      term.writeln(`Connecting to ${label}...`);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'cli_ready') {
          return;
        }
        if (data.type === 'cli_exit') {
          term.writeln(`\r\n[${label} exited with code ${data.code}]`);
          return;
        }
      } catch {
        // Raw terminal output — write directly to xterm
        term.write(event.data);
      }
    };

    ws.onclose = () => {
      log(`[${label}] WebSocket closed`);
      term.writeln('\r\n[Disconnected]');
    };

    ws.onerror = (e) => {
      logError(`[${label}] Error:`, e);
    };

    // Forward user keystrokes from xterm to WebSocket
    term.onData((data) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(data);
      }
    });

    // Send terminal dimensions so CLI can render properly
    const sendResize = () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }));
      }
    };
    term.onResize(sendResize);
    ws.addEventListener('open', () => sendResize());

    term.focus();

    return () => {
      window.removeEventListener('resize', handleResize);
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.onclose = null;
        ws.close();
      }
      cliWsRef.current = null;
      term.dispose();
      xtermRef.current = null;
      fitAddonRef.current = null;
    };
  }, [cliMode]);

  const sendMessage = () => {
    if (!input.trim() || isStreaming) return;

    const trimmed = input.trim();

    // Handle /clear command
    if (trimmed === '/clear') {
      setInput('');
      startNewConversation();
      return;
    }

    // Handle CLI commands
    if (trimmed === '/claude' || trimmed === '/gemini') {
      setInput('');
      setCliMode(trimmed.slice(1) as CliMode);
      return;
    }

    // Normal chat mode
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
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const loadConversation = async (id: number) => {
    try {
      const conv = await getConversation(id);
      setMessages(conv.messages.map((m) => ({ role: m.role as 'user' | 'assistant', content: m.content })));
      setConversationId(id);
      setShowSidebar(false);
    } catch {
      // ignore
    }
  };

  const handleDeleteConversation = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    await deleteConversation(id);
    if (conversationId === id) {
      setMessages([]);
      setConversationId(null);
    }
    loadConversations();
  };

  const startNewConversation = () => {
    setMessages([]);
    setConversationId(null);
    setShowSidebar(false);
  };

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
          {!wsConnected && !cliMode && <span className={styles.disconnected}> (reconnecting...)</span>}
        </span>
        {!cliMode && (
          <button
            className={`${styles.ttsToggle} ${ttsEnabled ? styles.ttsToggleActive : ''}`}
            onClick={handleTtsToggle}
            title={ttsEnabled ? (isSpeaking ? 'Speaking... (click to disable)' : 'Read aloud ON') : 'Read aloud'}
          >
            {isSpeaking ? '\uD83D\uDD0A' : '\uD83D\uDD08'}
          </button>
        )}
        {cliMode ? (
          <button className={styles.newChatButton} onClick={exitCliMode}>
            Exit
          </button>
        ) : (
          <button className={styles.newChatButton} onClick={startNewConversation}>
            +
          </button>
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
              placeholder="Type a message..."
              rows={1}
              disabled={isStreaming}
            />
            <VoiceButton
              onTranscription={(text) => setInput((prev) => prev ? `${prev} ${text}` : text)}
              disabled={isStreaming}
            />
            <button className={styles.sendButton} onClick={sendMessage} disabled={isStreaming || !input.trim()}>
              Send
            </button>
          </div>
        </>
      )}
    </div>
  );
}
