import { useState, useEffect, useCallback } from 'react';
import styles from './CalendarWidget.module.css';

const API_BASE = `${window.location.protocol}//${window.location.hostname}:8000/api`;

interface CalendarEvent {
  time: string;
  title: string;
}

export function CalendarWidget() {
  const [configured, setConfigured] = useState<boolean | null>(null);
  const [events, setEvents] = useState<CalendarEvent[]>([]);

  const checkStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/google/status`);
      const data = await res.json();
      setConfigured(data.configured);
    } catch {
      setConfigured(false);
    }
  }, []);

  useEffect(() => {
    checkStatus();
  }, [checkStatus]);

  const today = new Date();
  const dateStr = today.toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'short',
    day: 'numeric',
  });

  return (
    <div className={styles.calendar}>
      <div className={styles.header}>
        <span className={styles.title}>Calendar</span>
        <span className={styles.dateLabel}>{dateStr}</span>
      </div>

      {configured === null ? (
        <div className={styles.empty}>Loading...</div>
      ) : !configured ? (
        <div className={styles.notConfigured}>
          <p className={styles.notConfiguredText}>
            Google not configured. Set ASSISTANT_GOOGLE_CREDENTIALS_PATH in your .env file.
          </p>
        </div>
      ) : events.length === 0 ? (
        <div className={styles.empty}>
          Google connected. Ask the assistant to check your calendar, or events will appear here.
        </div>
      ) : (
        <div className={styles.eventList}>
          {events.map((event, i) => (
            <div key={i} className={styles.event}>
              <span className={styles.eventTime}>{event.time}</span>
              <span className={styles.eventTitle}>{event.title}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
