import { useState, useEffect, useCallback } from 'react';
import styles from './KanbanWidget.module.css';

import { API_BASE } from '../../services/api';
import { useWidgetCollapse } from '../../hooks/useWidgetCollapse';

interface Project {
  id: string;
  number: number;
  title: string;
  description: string;
  closed: boolean;
  owner: string;
}

interface ProjectItem {
  id: string;
  title: string;
  number: number | null;
  state: string;
  url: string;
}

interface Column {
  name: string;
  items: ProjectItem[];
}

interface IssueComment {
  author: string;
  body: string;
  created_at: string;
}

interface IssueDetail {
  number: number;
  title: string;
  state: string;
  body: string;
  url: string;
  author: string;
  assignees: string[];
  labels: string[];
  created_at: string;
  updated_at: string;
  comments: IssueComment[];
}

/** Parse owner/repo/number from a GitHub issue URL */
function parseIssueUrl(url: string): { owner: string; repo: string; number: number } | null {
  const m = url.match(/github\.com\/([^/]+)\/([^/]+)\/issues\/(\d+)/);
  if (!m) return null;
  return { owner: m[1], repo: m[2], number: parseInt(m[3], 10) };
}

function formatDate(iso: string): string {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
  });
}

type View = 'projects' | 'board' | 'ticket';

export function KanbanWidget() {
  const [collapsed, toggleCollapsed] = useWidgetCollapse('kanban');
  const [configured, setConfigured] = useState<boolean | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [sources, setSources] = useState<string[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [columns, setColumns] = useState<Column[]>([]);
  const [selectedIssue, setSelectedIssue] = useState<IssueDetail | null>(null);
  const [view, setView] = useState<View>('projects');
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [loadingBoard, setLoadingBoard] = useState(false);
  const [loadingTicket, setLoadingTicket] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAddSource, setShowAddSource] = useState(false);
  const [newSource, setNewSource] = useState('');
  const [addingSource, setAddingSource] = useState(false);

  const fetchSources = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/integrations/github/project-sources`);
      const data = await res.json();
      setSources(data.sources || []);
    } catch { /* ignore */ }
  }, []);

  const fetchProjects = useCallback(async () => {
    setLoadingProjects(true);
    try {
      const res = await fetch(`${API_BASE}/integrations/github/projects`);
      const data = await res.json();
      setConfigured(data.configured);
      if (data.error) {
        setError(data.error);
      } else {
        setError(null);
        setProjects(data.projects || []);
      }
    } catch {
      setConfigured(false);
    }
    setLoadingProjects(false);
  }, []);

  const fetchBoard = useCallback(async (project: Project) => {
    setLoadingBoard(true);
    setError(null);
    try {
      const res = await fetch(
        `${API_BASE}/integrations/github/projects/${encodeURIComponent(project.id)}/items`
      );
      const data = await res.json();
      if (data.error) {
        setError(data.error);
        setColumns([]);
      } else {
        setColumns(data.columns || []);
      }
    } catch {
      setError('Failed to load board');
      setColumns([]);
    }
    setLoadingBoard(false);
  }, []);

  const fetchTicket = useCallback(async (item: ProjectItem) => {
    const parsed = parseIssueUrl(item.url);
    if (!parsed) return;

    setLoadingTicket(true);
    setError(null);
    try {
      const res = await fetch(
        `${API_BASE}/integrations/github/issues/${parsed.owner}/${parsed.repo}/${parsed.number}`
      );
      const data = await res.json();
      if (data.error) {
        setError(data.error);
      } else {
        setSelectedIssue(data.issue);
        setView('ticket');
      }
    } catch {
      setError('Failed to load ticket');
    }
    setLoadingTicket(false);
  }, []);

  useEffect(() => {
    fetchSources();
    fetchProjects();
  }, [fetchSources, fetchProjects]);

  const addSource = async () => {
    const owner = newSource.trim();
    if (!owner) return;
    setAddingSource(true);
    try {
      const res = await fetch(`${API_BASE}/integrations/github/project-sources`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ owner }),
      });
      const data = await res.json();
      setSources(data.sources || []);
      setNewSource('');
      setShowAddSource(false);
      await fetchProjects();
    } catch { /* ignore */ }
    setAddingSource(false);
  };

  const removeSource = async (owner: string) => {
    try {
      const res = await fetch(
        `${API_BASE}/integrations/github/project-sources/${encodeURIComponent(owner)}`,
        { method: 'DELETE' },
      );
      const data = await res.json();
      setSources(data.sources || []);
      await fetchProjects();
    } catch { /* ignore */ }
  };

  const selectProject = (project: Project) => {
    setSelectedProject(project);
    setView('board');
    fetchBoard(project);
  };

  const goToBoard = () => {
    setSelectedIssue(null);
    setView('board');
    setError(null);
  };

  const goToProjects = () => {
    setSelectedProject(null);
    setSelectedIssue(null);
    setColumns([]);
    setView('projects');
    setError(null);
  };

  // Ticket detail view
  if (view === 'ticket' && selectedIssue) {
    return (
      <div className={styles.kanban}>
        <div className={styles.header}>
          <div className={styles.boardHeader}>
            <button className={styles.navButton} onClick={goToBoard}>{'\u2039'}</button>
            <span className={styles.title}>#{selectedIssue.number}</span>
          </div>
          <div className={styles.headerActions}>
            {selectedIssue.url && (
              <a
                href={selectedIssue.url}
                target="_blank"
                rel="noopener noreferrer"
                className={styles.externalLink}
              >
                Open
              </a>
            )}
            <button className={styles.collapseBtn} onClick={toggleCollapsed} title={collapsed ? 'Expand' : 'Collapse'}>
              {collapsed ? '\u25B8' : '\u25BE'}
            </button>
          </div>
        </div>

        {!collapsed && <div className={styles.ticketDetail}>
          <div className={styles.ticketTitle}>{selectedIssue.title}</div>

          <div className={styles.ticketMeta}>
            <span className={`${styles.ticketState} ${
              selectedIssue.state === 'open' ? styles.stateOpen : styles.stateClosed
            }`}>
              {selectedIssue.state}
            </span>
            <span className={styles.ticketMetaText}>
              opened by {selectedIssue.author} on {formatDate(selectedIssue.created_at)}
            </span>
          </div>

          {selectedIssue.assignees.length > 0 && (
            <div className={styles.ticketField}>
              <span className={styles.ticketFieldLabel}>Assignees</span>
              <span className={styles.ticketFieldValue}>
                {selectedIssue.assignees.join(', ')}
              </span>
            </div>
          )}

          {selectedIssue.labels.length > 0 && (
            <div className={styles.ticketField}>
              <span className={styles.ticketFieldLabel}>Labels</span>
              <div className={styles.ticketLabels}>
                {selectedIssue.labels.map((l) => (
                  <span key={l} className={styles.ticketLabel}>{l}</span>
                ))}
              </div>
            </div>
          )}

          {selectedIssue.body && (
            <div className={styles.ticketBody}>
              {selectedIssue.body}
            </div>
          )}

          {selectedIssue.comments.length > 0 && (
            <div className={styles.ticketComments}>
              <div className={styles.ticketFieldLabel}>
                Comments ({selectedIssue.comments.length})
              </div>
              {selectedIssue.comments.map((c, i) => (
                <div key={i} className={styles.ticketComment}>
                  <div className={styles.commentHeader}>
                    <span className={styles.commentAuthor}>{c.author}</span>
                    <span className={styles.commentDate}>{formatDate(c.created_at)}</span>
                  </div>
                  <div className={styles.commentBody}>{c.body}</div>
                </div>
              ))}
            </div>
          )}
        </div>}
      </div>
    );
  }

  // Board view
  if (view === 'board' && selectedProject) {
    return (
      <div className={styles.kanban}>
        <div className={styles.header}>
          <div className={styles.boardHeader}>
            <button className={styles.navButton} onClick={goToProjects}>{'\u2039'}</button>
            <span className={styles.title}>{selectedProject.title}</span>
          </div>
          <div className={styles.headerActions}>
            <button className={styles.navButton} onClick={() => fetchBoard(selectedProject)}>
              {'\u21BB'}
            </button>
            <button className={styles.collapseBtn} onClick={toggleCollapsed} title={collapsed ? 'Expand' : 'Collapse'}>
              {collapsed ? '\u25B8' : '\u25BE'}
            </button>
          </div>
        </div>

        {!collapsed && (
          loadingBoard ? (
            <div className={styles.helpText}>Loading board...</div>
          ) : error ? (
            <p className={styles.errorText}>{error}</p>
          ) : columns.length === 0 ? (
            <p className={styles.helpText}>No items in this project.</p>
          ) : (
            <div className={styles.board}>
              {columns.map((column) => (
                <div key={column.name} className={styles.column}>
                  <div className={styles.columnHeader}>
                    <span className={styles.columnName}>{column.name}</span>
                    <span className={styles.columnCount}>{column.items.length}</span>
                  </div>
                  <div className={styles.columnItems}>
                    {column.items.map((item) => (
                      <button
                        key={item.id}
                        className={styles.card}
                        onClick={() => item.url ? fetchTicket(item) : undefined}
                        disabled={loadingTicket || !item.url}
                      >
                        <span className={styles.cardTitle}>
                          {item.number && (
                            <span className={styles.cardNumber}>#{item.number}</span>
                          )}
                          {item.title}
                        </span>
                        {item.state && (
                          <span className={`${styles.cardState} ${
                            item.state === 'OPEN' ? styles.stateOpen :
                            item.state === 'CLOSED' ? styles.stateClosed : ''
                          }`}>
                            {item.state.toLowerCase()}
                          </span>
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )
        )}
      </div>
    );
  }

  // Project list view
  return (
    <div className={styles.kanban}>
      <div className={styles.header}>
        <span className={styles.title}>Projects</span>
        <div className={styles.headerActions}>
          {configured && (
            <span className={styles.statusConfigured}>GitHub</span>
          )}
          {configured === false && (
            <span className={styles.statusNotConfigured}>GitHub</span>
          )}
          <button className={styles.collapseBtn} onClick={toggleCollapsed} title={collapsed ? 'Expand' : 'Collapse'}>
            {collapsed ? '\u25B8' : '\u25BE'}
          </button>
        </div>
      </div>

      {!collapsed && (
        loadingProjects ? (
          <div className={styles.helpText}>Loading...</div>
        ) : !configured ? (
          <p className={styles.helpText}>
            Set ASSISTANT_GITHUB_TOKEN in your .env file to see your projects.
          </p>
        ) : (
        <>
          {error && <p className={styles.errorText}>{error}</p>}

          {projects.length > 0 ? (
            <div className={styles.projectList}>
              {projects.map((project) => (
                <button
                  key={project.id}
                  className={styles.projectCard}
                  onClick={() => selectProject(project)}
                >
                  <span className={styles.projectTitle}>{project.title}</span>
                  {project.owner && (
                    <span className={styles.projectOwner}>{project.owner}</span>
                  )}
                  {project.description && (
                    <span className={styles.projectDesc}>{project.description}</span>
                  )}
                </button>
              ))}
            </div>
          ) : (
            <div className={styles.helpText}>
              No projects found. Add a GitHub username below to see their projects.
            </div>
          )}

          {/* Sources management */}
          <div className={styles.sourcesSection}>
            {sources.length > 0 && (
              <div className={styles.sourcesList}>
                {sources.map((s) => (
                  <span key={s} className={styles.sourceChip}>
                    {s}
                    <button
                      className={styles.sourceRemove}
                      onClick={() => removeSource(s)}
                    >
                      {'\u00D7'}
                    </button>
                  </span>
                ))}
              </div>
            )}

            {showAddSource ? (
              <form
                className={styles.addSourceForm}
                onSubmit={(e) => { e.preventDefault(); addSource(); }}
              >
                <input
                  className={styles.addSourceInput}
                  type="text"
                  placeholder="GitHub username or org"
                  value={newSource}
                  onChange={(e) => setNewSource(e.target.value)}
                  autoFocus
                  disabled={addingSource}
                />
                <button
                  className={styles.addSourceSubmit}
                  type="submit"
                  disabled={addingSource || !newSource.trim()}
                >
                  {addingSource ? '...' : 'Add'}
                </button>
                <button
                  className={styles.addSourceCancel}
                  type="button"
                  onClick={() => { setShowAddSource(false); setNewSource(''); }}
                >
                  {'\u00D7'}
                </button>
              </form>
            ) : (
              <button
                className={styles.addSourceButton}
                onClick={() => setShowAddSource(true)}
              >
                + Add project source
              </button>
            )}
          </div>
        </>
        )
      )}
    </div>
  );
}
