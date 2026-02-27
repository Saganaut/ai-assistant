import { useState, useEffect, useCallback } from 'react';
import styles from './SchedulerWidget.module.css';

import { API_BASE } from '../../services/api';
import { useWidgetCollapse } from '../../hooks/useWidgetCollapse';

interface Schedule {
  id: number;
  name: string;
  cron_expression: string;
  prompt: string;
  enabled: boolean;
}

interface Template {
  name: string;
  cron_expression: string;
  prompt: string;
}

export function SchedulerWidget() {
  const [collapsed, toggleCollapsed] = useWidgetCollapse('scheduler');
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [showTemplates, setShowTemplates] = useState(false);

  const loadSchedules = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/schedules/`);
      setSchedules(await res.json());
    } catch {
      // ignore
    }
  }, []);

  const loadTemplates = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/schedules/templates`);
      setTemplates(await res.json());
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    loadSchedules();
    loadTemplates();
  }, [loadSchedules, loadTemplates]);

  const toggleSchedule = async (id: number, enabled: boolean) => {
    await fetch(`${API_BASE}/schedules/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: !enabled }),
    });
    loadSchedules();
  };

  const deleteSchedule = async (id: number) => {
    await fetch(`${API_BASE}/schedules/${id}`, { method: 'DELETE' });
    loadSchedules();
  };

  const addFromTemplate = async (template: Template) => {
    await fetch(`${API_BASE}/schedules/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(template),
    });
    setShowTemplates(false);
    loadSchedules();
  };

  return (
    <div className={styles.scheduler}>
      <div className={styles.header}>
        <span className={styles.title}>Scheduled Actions</span>
        <div className={styles.headerRight}>
          <button className={styles.addButton} onClick={() => setShowTemplates(!showTemplates)}>
            {showTemplates ? 'Cancel' : '+ Add'}
          </button>
          <button className={styles.collapseBtn} onClick={toggleCollapsed} title={collapsed ? 'Expand' : 'Collapse'}>
            {collapsed ? '\u25B8' : '\u25BE'}
          </button>
        </div>
      </div>

      {!collapsed && (
        <>
          {showTemplates && (
            <div className={styles.templateList}>
              {templates.map((t, i) => (
                <button key={i} className={styles.template} onClick={() => addFromTemplate(t)}>
                  <span className={styles.templateName}>{t.name}</span>
                  <span className={styles.templateCron}>{t.cron_expression}</span>
                </button>
              ))}
            </div>
          )}

          {schedules.length === 0 && !showTemplates && (
            <div className={styles.empty}>No scheduled actions. Click + Add to create one.</div>
          )}

          {schedules.length > 0 && (
            <div className={styles.list}>
              {schedules.map((s) => (
                <div key={s.id} className={styles.item}>
                  <button
                    className={s.enabled ? styles.toggleOn : styles.toggleOff}
                    onClick={() => toggleSchedule(s.id, s.enabled)}
                    title={s.enabled ? 'Disable' : 'Enable'}
                  />
                  <span className={styles.itemName}>{s.name}</span>
                  <span className={styles.itemCron}>{s.cron_expression}</span>
                  <button
                    className={styles.deleteButton}
                    onClick={() => deleteSchedule(s.id)}
                  >
                    {'\u2715'}
                  </button>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
