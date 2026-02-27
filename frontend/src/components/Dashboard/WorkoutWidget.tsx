import { useState, useEffect, useCallback } from 'react';
import styles from './WorkoutWidget.module.css';
import { RoutineEditor } from './RoutineEditor';
import {
  getRoutines,
  deleteRoutine,
  saveWorkoutLog,
  getWorkoutLog,
  getRecentWorkouts,
} from '../../services/api';
import type {
  WorkoutRoutine,
  RoutineExercise,
  ExerciseType,
  ExerciseLog,
  WorkoutLog,
} from '../../services/api';

// ── Helpers ───────────────────────────────────────────────────────────────────

function todayStr(): string {
  return new Date().toISOString().slice(0, 10);
}

function formatDateShort(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
}

function makeInitialLog(routine: WorkoutRoutine): WorkoutLog {
  const exercises: Record<string, ExerciseLog> = {};
  for (const section of routine.sections) {
    for (const ex of section.exercises) {
      exercises[ex.id] = {
        exerciseId: ex.id,
        progressionLevel: 0,
        sets: Array.from({ length: ex.defaultSets }, () => ({ reps: '', weight: '' })),
        done: false,
      };
    }
  }
  return { date: todayStr(), routineId: routine.id, exercises };
}

function dotClass(type: ExerciseType): string {
  if (type === 'warmup') return styles.typeDotWarmup;
  if (type === 'strength') return styles.typeDotStrength;
  return styles.typeDotCooldown;
}

function cardClass(type: ExerciseType): string {
  if (type === 'warmup') return styles.exerciseCardWarmup;
  if (type === 'strength') return styles.exerciseCardStrength;
  return styles.exerciseCardCooldown;
}

function sectionHeaderClass(type: ExerciseType): string {
  if (type === 'warmup') return styles.sectionHeaderWarmup;
  if (type === 'strength') return styles.sectionHeaderStrength;
  return styles.sectionHeaderCooldown;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function WorkoutWidget() {
  const [routines, setRoutines] = useState<WorkoutRoutine[]>([]);
  const [selectedId, setSelectedId] = useState<string>('bwf-rr');
  const [log, setLog] = useState<WorkoutLog | null>(null);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [recentDates, setRecentDates] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState('');
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingRoutine, setEditingRoutine] = useState<WorkoutRoutine | null>(null);

  const selectedRoutine = routines.find((r) => r.id === selectedId) ?? routines[0] ?? null;

  // ── Load routines + today's log ───────────────────────────────────────────

  const loadRoutines = useCallback(async () => {
    try {
      const data = await getRoutines();
      setRoutines(data);
      if (data.length > 0 && !data.find((r) => r.id === selectedId)) {
        setSelectedId(data[0].id);
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [selectedId]);

  const loadTodayLog = useCallback(
    async (routine: WorkoutRoutine) => {
      try {
        const data = await getWorkoutLog(todayStr());
        if (data.log && data.log.routineId === routine.id) {
          setLog(data.log);
        } else {
          setLog(makeInitialLog(routine));
        }
      } catch {
        setLog(makeInitialLog(routine));
      }
    },
    []
  );

  const loadRecent = useCallback(async () => {
    try {
      const data = await getRecentWorkouts();
      setRecentDates(data.dates);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    loadRoutines();
    loadRecent();
  }, [loadRoutines, loadRecent]);

  useEffect(() => {
    if (selectedRoutine) {
      loadTodayLog(selectedRoutine);
    }
  }, [selectedRoutine, loadTodayLog]);

  // ── Log mutation helpers ───────────────────────────────────────────────────

  function getExLog(exId: string, ex: RoutineExercise): ExerciseLog {
    return (
      log?.exercises[exId] ?? {
        exerciseId: exId,
        progressionLevel: 0,
        sets: Array.from({ length: ex.defaultSets }, () => ({ reps: '', weight: '' })),
        done: false,
      }
    );
  }

  function setExLog(exId: string, update: Partial<ExerciseLog>) {
    setLog((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        exercises: { ...prev.exercises, [exId]: { ...getExLogById(prev, exId), ...update } },
      };
    });
  }

  function getExLogById(logData: WorkoutLog, exId: string): ExerciseLog {
    return (
      logData.exercises[exId] ?? {
        exerciseId: exId,
        progressionLevel: 0,
        sets: [{ reps: '', weight: '' }],
        done: false,
      }
    );
  }

  function setSetField(exId: string, setIdx: number, field: 'reps' | 'weight', value: string) {
    setLog((prev) => {
      if (!prev) return prev;
      const existing = getExLogById(prev, exId);
      const sets = [...existing.sets];
      sets[setIdx] = { ...sets[setIdx], [field]: value };
      return {
        ...prev,
        exercises: { ...prev.exercises, [exId]: { ...existing, sets } },
      };
    });
  }

  function addSet(exId: string) {
    setLog((prev) => {
      if (!prev) return prev;
      const existing = getExLogById(prev, exId);
      const sets = [...existing.sets, { reps: '', weight: '' }];
      return {
        ...prev,
        exercises: { ...prev.exercises, [exId]: { ...existing, sets } },
      };
    });
  }

  function toggleExpanded(exId: string) {
    setExpanded((prev) => ({ ...prev, [exId]: !prev[exId] }));
  }

  // ── Save workout ───────────────────────────────────────────────────────────

  async function handleSave() {
    if (!log) return;
    setSaving(true);
    setSaveMsg('');
    try {
      await saveWorkoutLog({ ...log, date: todayStr() });
      setSaveMsg('Saved!');
      loadRecent();
    } catch {
      setSaveMsg('Save failed');
    } finally {
      setSaving(false);
      setTimeout(() => setSaveMsg(''), 3000);
    }
  }

  // ── Routine editor callbacks ───────────────────────────────────────────────

  function openNew() {
    setEditingRoutine(null);
    setEditorOpen(true);
  }

  function openEdit(r: WorkoutRoutine) {
    setEditingRoutine(r);
    setEditorOpen(true);
  }

  function handleEditorSave(saved: WorkoutRoutine) {
    setRoutines((prev) => {
      const idx = prev.findIndex((r) => r.id === saved.id);
      if (idx >= 0) {
        const next = [...prev];
        next[idx] = saved;
        return next;
      }
      return [...prev, saved];
    });
    setSelectedId(saved.id);
    setEditorOpen(false);
  }

  async function handleDelete(r: WorkoutRoutine) {
    if (!confirm(`Delete routine "${r.name}"? This cannot be undone.`)) return;
    try {
      await deleteRoutine(r.id);
      setRoutines((prev) => prev.filter((x) => x.id !== r.id));
      if (selectedId === r.id && routines.length > 1) {
        setSelectedId(routines.find((x) => x.id !== r.id)!.id);
      }
    } catch {
      // ignore
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className={styles.container}>
        <div style={{ color: 'var(--color-text-muted)', padding: 'var(--spacing-md)' }}>
          Loading routines…
        </div>
      </div>
    );
  }

  return (
    <>
      <div className={styles.container}>
        {/* Left column */}
        <div className={styles.leftCol}>
          <div>
            <div className={styles.sectionLabel} style={{ marginBottom: 6 }}>
              Routines
            </div>
            <div className={styles.routineList}>
              {routines.map((r) => (
                <div
                  key={r.id}
                  className={`${styles.routineRow} ${selectedId === r.id ? styles.routineRowActive : ''}`}
                >
                  <button
                    className={styles.routineBtn}
                    onClick={() => setSelectedId(r.id)}
                  >
                    {r.name}
                  </button>
                  <button
                    className={styles.routineActionBtn}
                    onClick={() => openEdit(r)}
                    title="Edit routine"
                  >
                    ✏
                  </button>
                  <button
                    className={`${styles.routineActionBtn} ${styles.routineActionBtnDanger}`}
                    onClick={() => handleDelete(r)}
                    title="Delete routine"
                  >
                    ✕
                  </button>
                </div>
              ))}
              <button className={styles.newRoutineBtn} onClick={openNew}>
                + New Routine
              </button>
            </div>
          </div>

          <div className={styles.recentSection}>
            <div className={styles.sectionLabel}>Recent (7 days)</div>
            {recentDates.length === 0 ? (
              <div style={{ color: 'var(--color-text-muted)', fontSize: '0.78rem' }}>
                No sessions yet
              </div>
            ) : (
              recentDates.slice(0, 7).map((d) => (
                <div key={d} className={styles.recentDay}>
                  <span className={styles.recentCheck}>✓</span>
                  <span>{formatDateShort(d)}</span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right column */}
        <div className={styles.rightCol}>
          {!selectedRoutine ? (
            <div style={{ color: 'var(--color-text-muted)', padding: 'var(--spacing-md)' }}>
              No routines yet.{' '}
              <button
                style={{ background: 'none', border: 'none', color: 'var(--color-accent)', cursor: 'pointer' }}
                onClick={openNew}
              >
                Create one
              </button>
            </div>
          ) : (
            <>
              <div className={styles.routineHeader}>
                <div className={styles.routineTitle}>{selectedRoutine.name}</div>
                {selectedRoutine.description && (
                  <div className={styles.routineDesc}>{selectedRoutine.description}</div>
                )}
              </div>

              {selectedRoutine.sections.map((section) => (
                <div key={section.name} className={styles.section}>
                  <div
                    className={`${styles.sectionHeader} ${sectionHeaderClass(section.type as ExerciseType)}`}
                  >
                    {section.name}
                  </div>

                  {section.exercises.map((ex) => {
                    const exLog = getExLog(ex.id, ex);
                    const isExpandedCard = expanded[ex.id] ?? false;
                    const currentProgression =
                      ex.progressions[exLog.progressionLevel] ?? ex.progressions[0];
                    const hasMultipleProgressions = ex.progressions.length > 1;
                    const isStrength = ex.type === 'strength';

                    return (
                      <div
                        key={ex.id}
                        className={`${styles.exerciseCard} ${cardClass(ex.type as ExerciseType)}`}
                      >
                        {/* Card header */}
                        <div
                          className={styles.exerciseHeader}
                          onClick={() => toggleExpanded(ex.id)}
                        >
                          <span
                            className={`${styles.typeDot} ${dotClass(ex.type as ExerciseType)}`}
                          />
                          <span className={styles.exerciseName}>{ex.name}</span>
                          {ex.repRange && (
                            <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                              {ex.repRange}
                            </span>
                          )}
                          <button
                            className={styles.expandBtn}
                            onClick={(e) => {
                              e.stopPropagation();
                              toggleExpanded(ex.id);
                            }}
                            aria-label="Toggle details"
                          >
                            {isExpandedCard ? '▾' : '▸'}
                          </button>
                        </div>

                        {/* Notes (inline, always visible when present) */}
                        {ex.notes && (
                          <div className={styles.exerciseNotes}>{ex.notes}</div>
                        )}

                        {/* Expanded description */}
                        {isExpandedCard && currentProgression && (
                          <div className={styles.expandedInfo}>
                            <span>{currentProgression.description}</span>
                            {ex.wikiUrl && (
                              <a
                                href={ex.wikiUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className={styles.wikiLink}
                                onClick={(e) => e.stopPropagation()}
                              >
                                BWF Wiki ↗
                              </a>
                            )}
                          </div>
                        )}

                        {/* Progression level selector (all types, only if >1 level) */}
                        {hasMultipleProgressions && (
                          <div className={styles.progressionRow}>
                            <span className={styles.progressionLabel}>Level:</span>
                            <select
                              className={styles.progressionSelect}
                              value={exLog.progressionLevel}
                              onChange={(e) =>
                                setExLog(ex.id, { progressionLevel: parseInt(e.target.value) })
                              }
                            >
                              {ex.progressions.map((p, i) => (
                                <option key={i} value={i}>
                                  L{i}: {p.name}
                                </option>
                              ))}
                            </select>
                          </div>
                        )}

                        {/* Single level: just show level name as label */}
                        {!hasMultipleProgressions && ex.progressions[0] && (
                          <div className={styles.progressionRow}>
                            <span className={styles.progressionLabel}>L0:</span>
                            <span
                              style={{
                                fontSize: '0.78rem',
                                color: 'var(--color-text-muted)',
                              }}
                            >
                              {ex.progressions[0].name}
                            </span>
                          </div>
                        )}

                        {/* Sets */}
                        <div className={styles.setsArea}>
                          {!isStrength ? (
                            // Warmup / cooldown: single done row
                            <div className={styles.setRow}>
                              <span className={styles.setLabel}>Done</span>
                              <input
                                type="text"
                                className={styles.setInput}
                                placeholder={ex.repRange || 'reps/time'}
                                value={exLog.sets[0]?.reps ?? ''}
                                onChange={(e) => setSetField(ex.id, 0, 'reps', e.target.value)}
                              />
                              <input
                                type="checkbox"
                                className={styles.setCheck}
                                checked={exLog.done}
                                onChange={(e) =>
                                  setExLog(ex.id, { done: e.target.checked })
                                }
                              />
                            </div>
                          ) : (
                            <>
                              {exLog.sets.map((s, idx) => (
                                <div key={idx} className={styles.setRow}>
                                  <span className={styles.setLabel}>Set {idx + 1}</span>
                                  <input
                                    type="text"
                                    className={styles.setInput}
                                    placeholder="reps"
                                    value={s.reps}
                                    onChange={(e) =>
                                      setSetField(ex.id, idx, 'reps', e.target.value)
                                    }
                                  />
                                  <input
                                    type="text"
                                    className={`${styles.setInput} ${styles.setInputWide}`}
                                    placeholder="weight (kg)"
                                    value={s.weight}
                                    onChange={(e) =>
                                      setSetField(ex.id, idx, 'weight', e.target.value)
                                    }
                                  />
                                </div>
                              ))}
                              <button
                                className={styles.addSetBtn}
                                onClick={() => addSet(ex.id)}
                              >
                                + Add set
                              </button>
                            </>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              ))}

              {/* Save */}
              <div className={styles.saveRow}>
                {saveMsg && <span className={styles.saveSuccess}>{saveMsg}</span>}
                <button
                  className={styles.saveBtn}
                  onClick={handleSave}
                  disabled={saving || !log}
                >
                  {saving ? 'Saving…' : 'Save Workout'}
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      {editorOpen && (
        <RoutineEditor
          routine={editingRoutine}
          onSave={handleEditorSave}
          onClose={() => setEditorOpen(false)}
        />
      )}
    </>
  );
}
