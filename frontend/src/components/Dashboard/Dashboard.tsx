import { useState } from 'react';
import { CalendarWidget } from './CalendarWidget';
import { KanbanWidget } from './KanbanWidget';
import { MarketsWidget } from './MarketsWidget';
import { QuickNotes } from './QuickNotes';
import { SchedulerWidget } from './SchedulerWidget';
import { WordPressWidget } from './WordPressWidget';
import { WorkoutWidget } from './WorkoutWidget';
import { FileBrowser } from '../FileBrowser/FileBrowser';
import { DraggableGrid } from './DraggableGrid';
import type { AppMode } from '../../contexts/ModeContext';
import styles from './Dashboard.module.css';

const DEFAULT_ORDER = ['markets', 'calendar', 'kanban', 'wordpress', 'scheduler', 'notes', 'files'];

const WIDGET_MAP: Record<string, React.ReactNode> = {
  markets: <MarketsWidget />,
  calendar: <CalendarWidget />,
  kanban: <KanbanWidget />,
  wordpress: <WordPressWidget />,
  scheduler: <SchedulerWidget />,
  notes: <QuickNotes />,
  files: <FileBrowser />,
};

const WIDGET_LABELS: Record<string, string> = {
  markets: 'Markets',
  calendar: 'Calendar',
  kanban: 'Kanban',
  wordpress: 'WordPress',
  scheduler: 'Scheduler',
  notes: 'Notes',
  files: 'Files',
};

const WORK_ORDER = ['calendar', 'kanban', 'scheduler', 'notes'];

function loadOrder(): string[] {
  try {
    const saved = localStorage.getItem('widget_order');
    if (saved) {
      const parsed: unknown = JSON.parse(saved);
      if (Array.isArray(parsed)) {
        const savedIds = parsed as string[];
        const merged = savedIds.filter((id) => DEFAULT_ORDER.includes(id));
        DEFAULT_ORDER.forEach((id) => {
          if (!merged.includes(id)) merged.push(id);
        });
        return merged;
      }
    }
  } catch {
    // ignore parse errors
  }
  return DEFAULT_ORDER;
}

type HealthTab = 'calendar' | 'notes';

interface DashboardProps {
  mode: AppMode;
}

export function Dashboard({ mode }: DashboardProps) {
  const [order, setOrder] = useState<string[]>(loadOrder);
  const [healthTab, setHealthTab] = useState<HealthTab>('calendar');
  const [healthTopCollapsed, setHealthTopCollapsed] = useState(false);

  const handleReorder = (newOrder: string[]) => {
    setOrder(newOrder);
    localStorage.setItem('widget_order', JSON.stringify(newOrder));
  };

  if (mode === 'health') {
    return (
      <div className={styles.healthContainer}>
        {/* Top: Calendar + Notes */}
        <div
          className={`${styles.healthTopSection} ${
            healthTopCollapsed ? styles.healthTopCollapsed : ''
          }`}
        >
          {/* Mobile-only tab bar */}
          <div className={styles.healthTopBar}>
            <button
              className={`${styles.healthTab} ${
                healthTab === 'calendar' ? styles.healthTabActive : ''
              }`}
              onClick={() => {
                setHealthTab('calendar');
                setHealthTopCollapsed(false);
              }}
            >
              Calendar
            </button>
            <button
              className={`${styles.healthTab} ${
                healthTab === 'notes' ? styles.healthTabActive : ''
              }`}
              onClick={() => {
                setHealthTab('notes');
                setHealthTopCollapsed(false);
              }}
            >
              Notes
            </button>
            <button
              className={styles.healthCollapseBtn}
              onClick={() => setHealthTopCollapsed((c) => !c)}
              title={healthTopCollapsed ? 'Expand' : 'Collapse'}
            >
              {healthTopCollapsed ? '▾' : '▴'}
            </button>
          </div>

          {/* Calendar */}
          <div
            className={`${styles.healthWidget} ${
              healthTab === 'calendar' ? styles.healthWidgetActive : ''
            }`}
          >
            <CalendarWidget />
          </div>

          {/* Notes */}
          <div
            className={`${styles.healthWidget} ${
              healthTab === 'notes' ? styles.healthWidgetActive : ''
            }`}
          >
            <QuickNotes />
          </div>
        </div>

        <WorkoutWidget />
      </div>
    );
  }

  if (mode === 'work') {
    const workItems = WORK_ORDER.map((id) => ({
      id,
      element: WIDGET_MAP[id],
      label: WIDGET_LABELS[id],
    }));
    return <DraggableGrid items={workItems} onReorder={() => {}} />;
  }

  // overview (default)
  const items = order.map((id) => ({
    id,
    element: WIDGET_MAP[id],
    label: WIDGET_LABELS[id],
  }));

  return <DraggableGrid items={items} onReorder={handleReorder} />;
}
