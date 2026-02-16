import styles from './Dashboard.module.css';

function Widget({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className={styles.widget}>
      <div className={styles.widgetHeader}>{title}</div>
      {children}
    </div>
  );
}

export function Dashboard() {
  return (
    <div className={styles.dashboard}>
      <Widget title="Projects">
        <p className={styles.placeholder}>GitHub Projects kanban - coming in v0.4</p>
      </Widget>
      <Widget title="Calendar">
        <p className={styles.placeholder}>Google Calendar - coming in v0.3</p>
      </Widget>
      <Widget title="Quick Notes">
        <p className={styles.placeholder}>Notes & health log - coming in v0.2</p>
      </Widget>
      <Widget title="Files">
        <p className={styles.placeholder}>Sandboxed file browser - coming in v0.1</p>
      </Widget>
    </div>
  );
}
