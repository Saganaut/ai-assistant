const API_BASE = `${window.location.protocol}//${window.location.hostname}:8000/api`;

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || res.statusText);
  }
  return res.json();
}

// Health
export const checkHealth = () => fetchJson<{ status: string; app: string }>('/health');

// Conversations
export interface ConversationSummary {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends ConversationSummary {
  messages: {
    id: number;
    role: string;
    content: string;
    created_at: string;
  }[];
}

export const listConversations = () =>
  fetchJson<ConversationSummary[]>('/conversations/');

export const getConversation = (id: number) =>
  fetchJson<ConversationDetail>(`/conversations/${id}`);

export const deleteConversation = (id: number) =>
  fetchJson<{ status: string }>(`/conversations/${id}`, { method: 'DELETE' });

// Files
export interface FileEntry {
  name: string;
  is_dir: boolean;
  size: number | null;
  modified: string;
}

export const listFiles = (path = '') =>
  fetchJson<{ path: string; entries: FileEntry[] }>(`/files/list?path=${encodeURIComponent(path)}`);

export const readFile = (path: string) =>
  fetchJson<{ path: string; content: string }>(`/files/read?path=${encodeURIComponent(path)}`);

export const writeFile = (path: string, content: string) =>
  fetchJson<{ path: string; status: string }>('/files/write', {
    method: 'POST',
    body: JSON.stringify({ path, content }),
  });

export const createDir = (path: string) =>
  fetchJson<{ path: string; status: string }>('/files/mkdir', {
    method: 'POST',
    body: JSON.stringify({ path }),
  });

export const deletePath = (path: string) =>
  fetchJson<{ path: string; status: string }>(`/files/delete?path=${encodeURIComponent(path)}`, {
    method: 'DELETE',
  });
