import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';

export type AppMode = 'overview' | 'health' | 'work';

interface ModeContextValue {
  mode: AppMode;
  setMode: (mode: AppMode) => void;
}

const ModeContext = createContext<ModeContextValue | null>(null);

function loadMode(): AppMode {
  const saved = localStorage.getItem('app_mode');
  if (saved === 'overview' || saved === 'health' || saved === 'work') return saved;
  return 'overview';
}

export function ModeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<AppMode>(loadMode);

  const setMode = (next: AppMode) => {
    setModeState(next);
    localStorage.setItem('app_mode', next);
  };

  // Keep in sync if another tab changes it
  useEffect(() => {
    const handler = (e: StorageEvent) => {
      if (e.key === 'app_mode' && e.newValue) {
        const val = e.newValue;
        if (val === 'overview' || val === 'health' || val === 'work') {
          setModeState(val);
        }
      }
    };
    window.addEventListener('storage', handler);
    return () => window.removeEventListener('storage', handler);
  }, []);

  return <ModeContext.Provider value={{ mode, setMode }}>{children}</ModeContext.Provider>;
}

export function useMode(): ModeContextValue {
  const ctx = useContext(ModeContext);
  if (!ctx) throw new Error('useMode must be used within ModeProvider');
  return ctx;
}
