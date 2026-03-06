/**
 * Lightweight error capture. Intercepts console.error and unhandledrejection,
 * stores entries in an immutable snapshot, notifies subscribers.
 *
 * Uses an immutable snapshot pattern so useSyncExternalStore gets a stable
 * reference between mutations (new array only when contents change).
 *
 * Call `initErrorCapture()` once at app startup.
 */

export interface ErrorEntry {
  id: number;
  ts: number;       // Date.now()
  type: 'console' | 'unhandled' | 'api';
  message: string;
  detail?: string;  // stack or extra context
}

const MAX_ENTRIES = 100;

// snapshot is replaced (new reference) on every mutation.
// getEntries() always returns the same reference between mutations —
// this is required for useSyncExternalStore to work correctly.
let snapshot: readonly ErrorEntry[] = [];
let nextId = 1;
const subscribers = new Set<() => void>();
let installed = false;

function notify() {
  subscribers.forEach((fn) => fn());
}

function push(entry: Omit<ErrorEntry, 'id' | 'ts'>) {
  const newEntry: ErrorEntry = { id: nextId++, ts: Date.now(), ...entry };
  const next = snapshot.length >= MAX_ENTRIES
    ? [...snapshot.slice(1), newEntry]
    : [...snapshot, newEntry];
  snapshot = next; // new reference → useSyncExternalStore detects the change
  notify();
}

/** Call once at app startup (idempotent). */
export function initErrorCapture() {
  if (installed) return;
  installed = true;

  // Intercept console.error
  const origError = console.error.bind(console);
  console.error = (...args: unknown[]) => {
    origError(...args);
    push({
      type: 'console',
      message: args
        .map((a) => (a instanceof Error ? a.message : String(a)))
        .join(' '),
      detail: (args.find((a) => a instanceof Error) as Error | undefined)?.stack,
    });
  };

  // Intercept unhandled promise rejections
  window.addEventListener('unhandledrejection', (e) => {
    const reason = e.reason;
    push({
      type: 'unhandled',
      message: reason instanceof Error ? reason.message : String(reason),
      detail: reason instanceof Error ? reason.stack : undefined,
    });
  });

  // Intercept uncaught errors
  window.addEventListener('error', (e) => {
    push({
      type: 'unhandled',
      message: e.message,
      detail: e.error?.stack,
    });
  });
}

/** Log an API error explicitly. */
export function logApiError(message: string, detail?: string) {
  push({ type: 'api', message, detail });
}

/** Returns a stable reference between mutations — safe for useSyncExternalStore. */
export function getEntries(): readonly ErrorEntry[] {
  return snapshot;
}

export function clearEntries() {
  snapshot = [];
  notify();
}

export function subscribe(fn: () => void): () => void {
  subscribers.add(fn);
  return () => subscribers.delete(fn);
}
