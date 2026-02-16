import styles from './Layout.module.css';
import { Chat } from '../Chat/Chat';
import { Dashboard } from '../Dashboard/Dashboard';

export function Layout() {
  return (
    <div className={styles.layout}>
      <header className={styles.header}>
        <span className={styles.headerTitle}>AI Assistant</span>
        <span className={styles.headerStatus}>● Connected</span>
      </header>
      <main className={styles.main}>
        <div className={styles.leftColumn}>
          <Dashboard />
        </div>
        <div className={styles.rightColumn}>
          <Chat />
        </div>
      </main>
    </div>
  );
}
