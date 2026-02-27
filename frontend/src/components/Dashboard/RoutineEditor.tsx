import { useState } from 'react';
import styles from './RoutineEditor.module.css';
import { createRoutine, updateRoutine } from '../../services/api';
import type { WorkoutRoutine, RoutineSection, RoutineExercise, RoutineProgression, ExerciseType } from '../../services/api';

// ── Helpers ───────────────────────────────────────────────────────────────────

function newId(): string {
  return crypto.randomUUID().slice(0, 8);
}

function newRoutine(): WorkoutRoutine {
  return {
    id: newId(),
    name: '',
    description: '',
    builtin: false,
    sections: [],
  };
}

function newExercise(): RoutineExercise {
  return {
    id: newId(),
    name: '',
    type: 'strength',
    repRange: '',
    notes: '',
    defaultSets: 3,
    wikiUrl: '',
    progressions: [{ name: '', description: '' }],
  };
}

function newSection(): RoutineSection {
  return { name: 'New Section', type: 'strength', exercises: [] };
}

function sectionBlockClass(type: ExerciseType): string {
  if (type === 'warmup') return `${styles.sectionBlock} ${styles.sectionBlockWarmup}`;
  if (type === 'strength') return `${styles.sectionBlock} ${styles.sectionBlockStrength}`;
  return `${styles.sectionBlock} ${styles.sectionBlockCooldown}`;
}

// ── Component ─────────────────────────────────────────────────────────────────

interface Props {
  routine: WorkoutRoutine | null; // null = create new
  onSave: (r: WorkoutRoutine) => void;
  onClose: () => void;
}

export function RoutineEditor({ routine, onSave, onClose }: Props) {
  const [draft, setDraft] = useState<WorkoutRoutine>(() =>
    routine ? JSON.parse(JSON.stringify(routine)) : newRoutine()
  );
  const [expandedEx, setExpandedEx] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const isNew = routine === null;

  // ── Draft mutation helpers ────────────────────────────────────────────────

  function setMeta(field: keyof Pick<WorkoutRoutine, 'name' | 'description'>, value: string) {
    setDraft((d) => ({ ...d, [field]: value }));
  }

  // Sections
  function addSection() {
    setDraft((d) => ({ ...d, sections: [...d.sections, newSection()] }));
  }

  function removeSection(si: number) {
    setDraft((d) => ({ ...d, sections: d.sections.filter((_, i) => i !== si) }));
  }

  function updateSectionField(si: number, field: keyof RoutineSection, value: string) {
    setDraft((d) => {
      const sections = [...d.sections];
      sections[si] = { ...sections[si], [field]: value } as RoutineSection;
      return { ...d, sections };
    });
  }

  // Exercises
  function addExercise(si: number) {
    const ex = newExercise();
    // Inherit section type
    ex.type = draft.sections[si].type;
    setDraft((d) => {
      const sections = [...d.sections];
      sections[si] = { ...sections[si], exercises: [...sections[si].exercises, ex] };
      return { ...d, sections };
    });
    setExpandedEx(ex.id);
  }

  function removeExercise(si: number, ei: number) {
    setDraft((d) => {
      const sections = [...d.sections];
      const exercises = sections[si].exercises.filter((_, i) => i !== ei);
      sections[si] = { ...sections[si], exercises };
      return { ...d, sections };
    });
  }

  function moveExercise(si: number, ei: number, dir: -1 | 1) {
    setDraft((d) => {
      const sections = [...d.sections];
      const exercises = [...sections[si].exercises];
      const target = ei + dir;
      if (target < 0 || target >= exercises.length) return d;
      [exercises[ei], exercises[target]] = [exercises[target], exercises[ei]];
      sections[si] = { ...sections[si], exercises };
      return { ...d, sections };
    });
  }

  function updateExerciseField(
    si: number,
    ei: number,
    field: keyof Omit<RoutineExercise, 'progressions' | 'id'>,
    value: string | number
  ) {
    setDraft((d) => {
      const sections = [...d.sections];
      const exercises = [...sections[si].exercises];
      exercises[ei] = { ...exercises[ei], [field]: value };
      sections[si] = { ...sections[si], exercises };
      return { ...d, sections };
    });
  }

  // Progressions
  function addProgression(si: number, ei: number) {
    setDraft((d) => {
      const sections = [...d.sections];
      const exercises = [...sections[si].exercises];
      const progressions: RoutineProgression[] = [
        ...exercises[ei].progressions,
        { name: '', description: '' },
      ];
      exercises[ei] = { ...exercises[ei], progressions };
      sections[si] = { ...sections[si], exercises };
      return { ...d, sections };
    });
  }

  function removeProgression(si: number, ei: number, pi: number) {
    setDraft((d) => {
      const sections = [...d.sections];
      const exercises = [...sections[si].exercises];
      const progressions = exercises[ei].progressions.filter((_, i) => i !== pi);
      exercises[ei] = { ...exercises[ei], progressions };
      sections[si] = { ...sections[si], exercises };
      return { ...d, sections };
    });
  }

  function updateProgression(
    si: number,
    ei: number,
    pi: number,
    field: keyof RoutineProgression,
    value: string
  ) {
    setDraft((d) => {
      const sections = [...d.sections];
      const exercises = [...sections[si].exercises];
      const progressions = [...exercises[ei].progressions];
      progressions[pi] = { ...progressions[pi], [field]: value };
      exercises[ei] = { ...exercises[ei], progressions };
      sections[si] = { ...sections[si], exercises };
      return { ...d, sections };
    });
  }

  // ── Save ──────────────────────────────────────────────────────────────────

  async function handleSave() {
    if (!draft.name.trim()) {
      setError('Routine name is required.');
      return;
    }
    setSaving(true);
    setError('');
    try {
      let saved: WorkoutRoutine;
      if (isNew) {
        saved = await createRoutine(draft);
      } else {
        saved = await updateRoutine(draft.id, draft);
      }
      onSave(saved);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className={styles.header}>
          <span className={styles.headerTitle}>
            {isNew ? 'New Routine' : `Edit: ${routine!.name}`}
          </span>
          <button className={styles.closeBtn} onClick={onClose}>×</button>
        </div>

        {/* Body */}
        <div className={styles.body}>
          {/* Name + description */}
          <div className={styles.metaFields}>
            <div>
              <div className={styles.fieldLabel}>Name</div>
              <input
                className={styles.textInput}
                value={draft.name}
                onChange={(e) => setMeta('name', e.target.value)}
                placeholder="e.g. BWF Recommended Routine"
              />
            </div>
            <div>
              <div className={styles.fieldLabel}>Description</div>
              <textarea
                className={styles.textareaInput}
                value={draft.description}
                onChange={(e) => setMeta('description', e.target.value)}
                placeholder="Brief description of the routine"
              />
            </div>
          </div>

          {/* Sections */}
          {draft.sections.map((section, si) => (
            <div key={si} className={sectionBlockClass(section.type as ExerciseType)}>
              {/* Section meta row */}
              <div className={styles.sectionMeta}>
                <input
                  className={styles.sectionNameInput}
                  value={section.name}
                  onChange={(e) => updateSectionField(si, 'name', e.target.value)}
                  placeholder="Section name"
                />
                <select
                  className={styles.typeSelect}
                  value={section.type}
                  onChange={(e) => updateSectionField(si, 'type', e.target.value)}
                >
                  <option value="warmup">Warm-up</option>
                  <option value="strength">Strength</option>
                  <option value="cooldown">Cool-down</option>
                </select>
                <button
                  className={`${styles.iconBtn} ${styles.iconBtnDanger}`}
                  onClick={() => removeSection(si)}
                  title="Remove section"
                >
                  ✕
                </button>
              </div>

              {/* Exercises */}
              <div className={styles.exerciseList}>
                {section.exercises.map((ex, ei) => {
                  const isExpanded = expandedEx === ex.id;
                  return (
                    <div key={ex.id} className={styles.exerciseRow}>
                      {/* Compact header */}
                      <div className={styles.exerciseRowHeader}>
                        <button
                          className={styles.iconBtn}
                          onClick={() => moveExercise(si, ei, -1)}
                          title="Move up"
                        >
                          ↑
                        </button>
                        <button
                          className={styles.iconBtn}
                          onClick={() => moveExercise(si, ei, 1)}
                          title="Move down"
                        >
                          ↓
                        </button>
                        <span className={styles.exRowName}>
                          {ex.name || <em style={{ color: 'var(--color-text-muted)' }}>Unnamed exercise</em>}
                        </span>
                        {ex.repRange && (
                          <span className={styles.exRowMeta}>{ex.repRange}</span>
                        )}
                        <button
                          className={styles.iconBtn}
                          onClick={() => setExpandedEx(isExpanded ? null : ex.id)}
                          title={isExpanded ? 'Collapse' : 'Edit'}
                        >
                          {isExpanded ? '▴' : '✏'}
                        </button>
                        <button
                          className={`${styles.iconBtn} ${styles.iconBtnDanger}`}
                          onClick={() => removeExercise(si, ei)}
                          title="Remove exercise"
                        >
                          ✕
                        </button>
                      </div>

                      {/* Expanded edit form */}
                      {isExpanded && (
                        <div className={styles.exerciseEditForm}>
                          {/* Name */}
                          <div className={styles.formRow}>
                            <span className={styles.formRowLabel}>Name</span>
                            <div className={styles.formRowField}>
                              <input
                                className={styles.smallInput}
                                value={ex.name}
                                onChange={(e) => updateExerciseField(si, ei, 'name', e.target.value)}
                                placeholder="Exercise name"
                              />
                            </div>
                          </div>

                          {/* Type + RepRange + DefaultSets */}
                          <div className={styles.formRow}>
                            <span className={styles.formRowLabel}>Type</span>
                            <div className={styles.formRowSplit}>
                              <select
                                className={styles.smallInput}
                                value={ex.type}
                                onChange={(e) => updateExerciseField(si, ei, 'type', e.target.value)}
                              >
                                <option value="warmup">Warm-up</option>
                                <option value="strength">Strength</option>
                                <option value="cooldown">Cool-down</option>
                              </select>
                              <input
                                className={styles.smallInput}
                                value={ex.repRange}
                                onChange={(e) => updateExerciseField(si, ei, 'repRange', e.target.value)}
                                placeholder="Rep range (e.g. 5-8)"
                              />
                              <input
                                className={styles.smallInput}
                                type="number"
                                min={1}
                                max={10}
                                value={ex.defaultSets}
                                onChange={(e) =>
                                  updateExerciseField(si, ei, 'defaultSets', parseInt(e.target.value) || 1)
                                }
                                style={{ width: 64 }}
                                title="Default sets"
                                placeholder="Sets"
                              />
                            </div>
                          </div>

                          {/* Notes */}
                          <div className={styles.formRow}>
                            <span className={styles.formRowLabel}>Notes</span>
                            <div className={styles.formRowField}>
                              <input
                                className={styles.smallInput}
                                value={ex.notes}
                                onChange={(e) => updateExerciseField(si, ei, 'notes', e.target.value)}
                                placeholder="Contextual comment (e.g. Add after Negative Pullups)"
                              />
                            </div>
                          </div>

                          {/* Wiki URL */}
                          <div className={styles.formRow}>
                            <span className={styles.formRowLabel}>Wiki URL</span>
                            <div className={styles.formRowField}>
                              <input
                                className={styles.smallInput}
                                value={ex.wikiUrl}
                                onChange={(e) => updateExerciseField(si, ei, 'wikiUrl', e.target.value)}
                                placeholder="https://..."
                              />
                            </div>
                          </div>

                          {/* Progressions */}
                          <div className={styles.formRow}>
                            <span className={styles.formRowLabel}>Levels</span>
                            <div className={styles.formRowField}>
                              <div className={styles.progressionList}>
                                {ex.progressions.map((p, pi) => (
                                  <div key={pi} className={styles.progressionItem}>
                                    <span className={styles.progressionLevel}>L{pi}</span>
                                    <div className={styles.progressionFields}>
                                      <input
                                        className={styles.smallInput}
                                        value={p.name}
                                        onChange={(e) =>
                                          updateProgression(si, ei, pi, 'name', e.target.value)
                                        }
                                        placeholder="Level name"
                                      />
                                      <input
                                        className={styles.smallInput}
                                        value={p.description}
                                        onChange={(e) =>
                                          updateProgression(si, ei, pi, 'description', e.target.value)
                                        }
                                        placeholder="How to perform it"
                                      />
                                    </div>
                                    <button
                                      className={`${styles.iconBtn} ${styles.iconBtnDanger}`}
                                      onClick={() => removeProgression(si, ei, pi)}
                                      title="Remove level"
                                      style={{ marginTop: 4 }}
                                    >
                                      ✕
                                    </button>
                                  </div>
                                ))}
                              </div>
                              <button
                                className={styles.addLinkBtn}
                                onClick={() => addProgression(si, ei)}
                                style={{ marginTop: 4 }}
                              >
                                + Add Level
                              </button>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Add exercise */}
              <button className={styles.addExBtn} onClick={() => addExercise(si)}>
                + Add Exercise
              </button>
            </div>
          ))}

          {/* Add section */}
          <button className={styles.addSectionBtn} onClick={addSection}>
            + Add Section
          </button>
        </div>

        {/* Footer */}
        <div className={styles.footer}>
          {error && <span className={styles.errorMsg}>{error}</span>}
          <button className={styles.cancelBtn} onClick={onClose}>
            Cancel
          </button>
          <button className={styles.saveBtn} onClick={handleSave} disabled={saving}>
            {saving ? 'Saving…' : 'Save Routine'}
          </button>
        </div>
      </div>
    </div>
  );
}
