import { useState, useEffect, useCallback } from 'react';
import styles from './QuickNotes.module.css';

import { API_BASE } from '../../services/api';
import { useWidgetCollapse } from '../../hooks/useWidgetCollapse';

interface NoteFile {
  path: string;
  name: string;
  modified: string;
}

type Tab = 'notes' | 'health';

export function QuickNotes() {
  const [collapsed, toggleCollapsed] = useWidgetCollapse('quicknotes');
  const [tab, setTab] = useState<Tab>('notes');
  const [noteText, setNoteText] = useState('');
  const [noteFiles, setNoteFiles] = useState<NoteFile[]>([]);
  const [viewingNote, setViewingNote] = useState<{ path: string; content: string } | null>(null);
  const [saving, setSaving] = useState(false);
  const [savedMsg, setSavedMsg] = useState('');

  const loadNotes = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/notes/list?folder=${tab}`);
      const data = await res.json();
      setNoteFiles(data.files || []);
    } catch {
      // API may not be ready
    }
  }, [tab]);

  useEffect(() => {
    loadNotes();
    setViewingNote(null);
  }, [loadNotes]);

  const handleSave = async () => {
    if (!noteText.trim()) return;
    setSaving(true);
    setSavedMsg('');

    const endpoint = tab === 'health' ? '/notes/health' : '/notes/quick';
    const body = tab === 'health'
      ? { content: noteText.trim(), category: 'general' }
      : { content: noteText.trim(), title: 'Quick Note' };

    try {
      await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      setNoteText('');
      setSavedMsg('Saved!');
      loadNotes();
      setTimeout(() => setSavedMsg(''), 2000);
    } catch {
      setSavedMsg('Error saving');
    } finally {
      setSaving(false);
    }
  };

  const viewNote = async (path: string) => {
    try {
      const res = await fetch(`${API_BASE}/notes/read?path=${encodeURIComponent(path)}`);
      const data = await res.json();
      setViewingNote({ path, content: data.content });
    } catch {
      // ignore
    }
  };

  return (
    <div className={styles.quickNotes}>
      <div className={styles.header}>
        <span className={styles.title}>Quick Notes</span>
        <div className={styles.headerRight}>
          <div className={styles.tabs}>
            <button
              className={tab === 'notes' ? styles.tabActive : styles.tab}
              onClick={() => setTab('notes')}
            >
              Notes
            </button>
            <button
              className={tab === 'health' ? styles.tabActive : styles.tab}
              onClick={() => setTab('health')}
            >
              Health
            </button>
          </div>
          <button className={styles.collapseBtn} onClick={toggleCollapsed} title={collapsed ? 'Expand' : 'Collapse'}>
            {collapsed ? '\u25B8' : '\u25BE'}
          </button>
        </div>
      </div>

      {!collapsed && (
        <>
          <div className={styles.inputRow}>
            <textarea
              className={styles.noteInput}
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
              placeholder={tab === 'health' ? 'Log health/fitness note...' : 'Quick note...'}
              rows={2}
            />
            <button
              className={styles.saveButton}
              onClick={handleSave}
              disabled={saving || !noteText.trim()}
            >
              Save
            </button>
          </div>
          {savedMsg && <span className={styles.saved}>{savedMsg}</span>}
          {viewingNote ? (
            <>
              <button className={styles.backLink} onClick={() => setViewingNote(null)}>
                Back to list
              </button>
              <pre className={styles.noteContent}>{viewingNote.content}</pre>
            </>
          ) : noteFiles.length === 0 ? (
            <div className={styles.empty}>No {tab === 'health' ? 'health logs' : 'notes'} yet</div>
          ) : (
            <div className={styles.notesList}>
              {noteFiles.slice(0, 10).map((f) => (
                <button key={f.path} className={styles.noteFile} onClick={() => viewNote(f.path)}>
                  <span className={styles.noteFileName}>{f.name}</span>
                  <span className={styles.noteDate}>{new Date(f.modified).toLocaleDateString()}</span>
                </button>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
