import { useState, useEffect, useCallback } from 'react';
import { listFiles, readFile, type FileEntry } from '../../services/api';
import styles from './FileBrowser.module.css';

function formatSize(bytes: number | null): string {
  if (bytes === null) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function FileBrowser() {
  const [currentPath, setCurrentPath] = useState('');
  const [entries, setEntries] = useState<FileEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewingFile, setViewingFile] = useState<{ name: string; content: string } | null>(null);

  const loadDir = useCallback(async (path: string) => {
    setLoading(true);
    setError(null);
    setViewingFile(null);
    try {
      const data = await listFiles(path);
      setEntries(data.entries);
      setCurrentPath(path);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load directory');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDir('');
  }, [loadDir]);

  const handleEntryClick = async (entry: FileEntry) => {
    const entryPath = currentPath ? `${currentPath}/${entry.name}` : entry.name;
    if (entry.is_dir) {
      loadDir(entryPath);
    } else {
      try {
        const data = await readFile(entryPath);
        setViewingFile({ name: entry.name, content: data.content });
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to read file');
      }
    }
  };

  const navigateUp = () => {
    const parts = currentPath.split('/').filter(Boolean);
    parts.pop();
    loadDir(parts.join('/'));
  };

  const breadcrumbParts = currentPath.split('/').filter(Boolean);

  return (
    <div className={styles.fileBrowser}>
      <div className={styles.header}>
        <span className={styles.title}>Files</span>
      </div>

      <div className={styles.breadcrumb}>
        <button className={styles.breadcrumbLink} onClick={() => loadDir('')}>
          ~/data
        </button>
        {breadcrumbParts.map((part, i) => {
          const path = breadcrumbParts.slice(0, i + 1).join('/');
          return (
            <span key={path}>
              {' / '}
              <button className={styles.breadcrumbLink} onClick={() => loadDir(path)}>
                {part}
              </button>
            </span>
          );
        })}
      </div>

      {viewingFile ? (
        <div className={styles.fileViewer}>
          <div className={styles.fileViewerHeader}>
            <span className={styles.fileViewerName}>{viewingFile.name}</span>
            <button className={styles.backButton} onClick={() => setViewingFile(null)}>
              Back
            </button>
          </div>
          <pre className={styles.fileContent}>{viewingFile.content}</pre>
        </div>
      ) : loading ? (
        <div className={styles.loading}>Loading...</div>
      ) : error ? (
        <div className={styles.error}>{error}</div>
      ) : entries.length === 0 ? (
        <div className={styles.empty}>Empty directory</div>
      ) : (
        <div className={styles.entries}>
          {currentPath && (
            <button className={styles.entry} onClick={navigateUp}>
              <span className={styles.entryIcon}>..</span>
              <span className={styles.entryName}>(parent directory)</span>
            </button>
          )}
          {entries.map((entry) => (
            <button
              key={entry.name}
              className={styles.entry}
              onClick={() => handleEntryClick(entry)}
            >
              <span className={styles.entryIcon}>{entry.is_dir ? '\uD83D\uDCC1' : '\uD83D\uDCC4'}</span>
              <span className={styles.entryName}>{entry.name}</span>
              <span className={styles.entryMeta}>{formatSize(entry.size)}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
