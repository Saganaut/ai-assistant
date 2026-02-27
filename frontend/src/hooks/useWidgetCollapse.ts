import { useState } from 'react';

export function useWidgetCollapse(id: string): [boolean, () => void] {
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    try {
      return localStorage.getItem(`widget_collapsed_${id}`) === 'true';
    } catch {
      return false;
    }
  });

  const toggle = () => {
    setCollapsed(c => {
      const next = !c;
      try {
        localStorage.setItem(`widget_collapsed_${id}`, String(next));
      } catch { /* ignore */ }
      return next;
    });
  };

  return [collapsed, toggle];
}
