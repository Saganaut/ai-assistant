import { useState, useEffect, useCallback } from 'react';
import styles from './CalendarWidget.module.css';

import { API_BASE } from '../../services/api';
import { useWidgetCollapse } from '../../hooks/useWidgetCollapse';

interface CalendarEvent {
  id: string;
  title: string;
  start: string;
  end: string;
  location: string;
  all_day: boolean;
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
}

function formatTimeRange(event: CalendarEvent): string {
  if (event.all_day) return 'All day';
  return `${formatTime(event.start)} – ${formatTime(event.end)}`;
}

function toDateString(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

export function CalendarWidget() {
  const [collapsed, toggleCollapsed] = useWidgetCollapse('calendar');
  const [configured, setConfigured] = useState<boolean | null>(null);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState(() => new Date());

  const fetchEvents = useCallback(async (date: Date) => {
    setLoading(true);
    try {
      const dateParam = toDateString(date);
      const res = await fetch(`${API_BASE}/integrations/calendar/events?date=${dateParam}`);
      const data = await res.json();
      setConfigured(data.configured);
      if (data.error) {
        setError(data.error);
        setEvents([]);
      } else {
        setError(null);
        setEvents(data.events || []);
      }
    } catch {
      setConfigured(false);
      setError(null);
      setEvents([]);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchEvents(selectedDate);
  }, [selectedDate, fetchEvents]);

  // Refresh every 5 minutes
  useEffect(() => {
    const interval = setInterval(() => fetchEvents(selectedDate), 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [selectedDate, fetchEvents]);

  const goToDay = (offset: number) => {
    setSelectedDate(prev => {
      const next = new Date(prev);
      next.setDate(next.getDate() + offset);
      return next;
    });
  };

  const isToday =
    toDateString(selectedDate) === toDateString(new Date());

  const dateStr = selectedDate.toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'short',
    day: 'numeric',
  });

  // Check if an event is happening now
  const now = new Date();
  const isCurrentEvent = (event: CalendarEvent) => {
    if (event.all_day) return false;
    const start = new Date(event.start);
    const end = new Date(event.end);
    return now >= start && now < end;
  };

  return (
    <div className={styles.calendar}>
      <div className={styles.header}>
        <span className={styles.title}>Calendar</span>
        <div className={styles.headerRight}>
          <div className={styles.dateNav}>
            <button className={styles.navButton} onClick={() => goToDay(-1)}>{'\u2039'}</button>
            <button
              className={`${styles.dateLabel} ${!isToday ? styles.dateLabelClickable : ''}`}
              onClick={() => setSelectedDate(new Date())}
            >
              {isToday ? 'Today' : dateStr}
            </button>
            <button className={styles.navButton} onClick={() => goToDay(1)}>{'\u203A'}</button>
          </div>
          <button className={styles.collapseBtn} onClick={toggleCollapsed} title={collapsed ? 'Expand' : 'Collapse'}>
            {collapsed ? '\u25B8' : '\u25BE'}
          </button>
        </div>
      </div>

      {!collapsed && (
        <>
          {!isToday && <div className={styles.dateSub}>{dateStr}</div>}
          {loading ? (
            <div className={styles.empty}>Loading...</div>
          ) : !configured ? (
            <div className={styles.notConfigured}>
              <p className={styles.notConfiguredText}>
                Google not configured. Set ASSISTANT_GOOGLE_CREDENTIALS_PATH in your .env file.
              </p>
            </div>
          ) : error ? (
            <div className={styles.errorText}>
              Could not load calendar. Check credentials.
            </div>
          ) : events.length === 0 ? (
            <div className={styles.empty}>No events{isToday ? ' today' : ''}.</div>
          ) : (
            <div className={styles.eventList}>
              {events.map((event) => (
                <div
                  key={event.id}
                  className={`${styles.event} ${isCurrentEvent(event) ? styles.eventCurrent : ''}`}
                >
                  <div className={styles.eventTime}>{formatTimeRange(event)}</div>
                  <div className={styles.eventDetails}>
                    <span className={styles.eventTitle}>{event.title}</span>
                    {event.location && (
                      <span className={styles.eventLocation}>{event.location}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
