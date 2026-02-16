import { CalendarWidget } from './CalendarWidget';
import { KanbanWidget } from './KanbanWidget';
import { QuickNotes } from './QuickNotes';
import { SchedulerWidget } from './SchedulerWidget';
import { FileBrowser } from '../FileBrowser/FileBrowser';
import styles from './Dashboard.module.css';

export function Dashboard() {
  return (
    <div className={styles.dashboard}>
      <KanbanWidget />
      <CalendarWidget />
      <SchedulerWidget />
      <QuickNotes />
      <FileBrowser />
    </div>
  );
}
