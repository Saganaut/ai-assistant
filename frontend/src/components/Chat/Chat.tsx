import { useState, useRef, useEffect, useCallback } from 'react';
import { listConversations, getConversation, deleteConversation, type ConversationSummary } from '../../services/api';
import { VoiceButton } from './VoiceButton';
import styles from './Chat.module.css';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [showSidebar, setShowSidebar] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttempts = useRef(0);
  const unmountedRef = useRef(false);

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

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.hostname}:8000/api/chat/ws`);
    wsRef.current = ws;

    ws.onopen = () => {
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
      reconnectTimeout.current = setTimeout(connectWebSocket, delay);
    };

    ws.onerror = () => {
      // onclose will fire after this, which handles reconnect
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
    };
  }, [connectWebSocket]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = () => {
    if (!input.trim() || isStreaming) return;
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      connectWebSocket();
      return;
    }

    const userMessage: Message = { role: 'user', content: input.trim() };
    setMessages((prev) => [...prev, userMessage]);

    const payload = conversationId
      ? JSON.stringify({ content: input.trim(), conversation_id: conversationId })
      : input.trim();

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
          {conversationId ? `Chat #${conversationId}` : 'New Chat'}
          {!wsConnected && <span className={styles.disconnected}> (reconnecting...)</span>}
        </span>
        <button className={styles.newChatButton} onClick={startNewConversation}>
          +
        </button>
      </div>

      {showSidebar && (
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
                  \u2715
                </button>
              </div>
            ))
          )}
        </div>
      )}

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
    </div>
  );
}
