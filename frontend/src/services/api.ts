export const API_BASE = import.meta.env.VITE_API_BASE || '/api';

export function getWsBase(): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  if (import.meta.env.VITE_API_BASE) {
    // Explicit base URL configured — derive WS from it
    const url = new URL(import.meta.env.VITE_API_BASE);
    return `${protocol}//${url.host}${url.pathname}`;
  }
  // Same origin
  return `${protocol}//${window.location.host}/api`;
}

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

// Integrations
export interface IntegrationStatus {
  google: {
    configured: boolean;
    connected: boolean;
    services: string[];
  };
  github: {
    configured: boolean;
    connected: boolean;
  };
  wordpress: {
    configured: boolean;
    connected: boolean;
  };
}

export const getIntegrationStatus = () =>
  fetchJson<IntegrationStatus>('/integrations/status');

// Workouts — types
export type ExerciseType = 'warmup' | 'strength' | 'cooldown';

export interface RoutineProgression {
  name: string;
  description: string;
}

export interface RoutineExercise {
  id: string;
  name: string;
  type: ExerciseType;
  repRange: string;
  notes: string;
  defaultSets: number;
  wikiUrl: string;
  progressions: RoutineProgression[];
}

export interface RoutineSection {
  name: string;
  type: ExerciseType;
  exercises: RoutineExercise[];
}

export interface WorkoutRoutine {
  id: string;
  name: string;
  description: string;
  builtin: boolean;
  sections: RoutineSection[];
}

export interface SetLog { reps: string; weight: string; }
export interface ExerciseLog {
  exerciseId: string;
  progressionLevel: number;
  sets: SetLog[];
  done: boolean;
}
export interface WorkoutLog {
  date: string;
  routineId: string;
  exercises: Record<string, ExerciseLog>;
}

// Workouts — routines CRUD
export const getRoutines = () => fetchJson<WorkoutRoutine[]>('/workouts/routines');
export const getRoutine = (id: string) => fetchJson<WorkoutRoutine>(`/workouts/routines/${id}`);
export const createRoutine = (r: WorkoutRoutine) =>
  fetchJson<WorkoutRoutine>('/workouts/routines', { method: 'POST', body: JSON.stringify(r) });
export const updateRoutine = (id: string, r: WorkoutRoutine) =>
  fetchJson<WorkoutRoutine>(`/workouts/routines/${id}`, { method: 'PUT', body: JSON.stringify(r) });
export const deleteRoutine = (id: string) =>
  fetchJson<{ status: string }>(`/workouts/routines/${id}`, { method: 'DELETE' });

// Workouts — logs
export const getWorkoutLog = (date: string) =>
  fetchJson<{ date: string; log: WorkoutLog | null }>(`/workouts/logs?date=${encodeURIComponent(date)}`);

export const saveWorkoutLog = (log: WorkoutLog) =>
  fetchJson<{ status: string; date: string }>('/workouts/logs', {
    method: 'POST',
    body: JSON.stringify(log),
  });

export const getRecentWorkouts = () =>
  fetchJson<{ dates: string[] }>('/workouts/recent');
