import styles from './KanbanWidget.module.css';

export function KanbanWidget() {
  // For now, this is a placeholder that instructs the user to interact via chat.
  // The GitHub token is configured server-side via env vars.
  // In the future, this could fetch project items directly.

  return (
    <div className={styles.kanban}>
      <div className={styles.header}>
        <span className={styles.title}>Projects</span>
        <span className={styles.statusNotConfigured}>GitHub</span>
      </div>
      <p className={styles.helpText}>
        Set ASSISTANT_GITHUB_TOKEN in your .env file, then ask the assistant to list your GitHub projects, issues, or repos.
      </p>
    </div>
  );
}
