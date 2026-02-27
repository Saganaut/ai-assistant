import { useState, useEffect, useCallback } from 'react';
import styles from './MarketsWidget.module.css';
import { API_BASE } from '../../services/api';
import { useWidgetCollapse } from '../../hooks/useWidgetCollapse';

interface Quote {
  symbol: string;
  name: string;
  price: number;
  change: number;
  change_pct: number;
}

interface NewsItem {
  title: string;
  url: string;
  source: string;
  published: string;
}

interface Snapshot {
  indexes: Quote[];
  macro: Quote[];
  watchlist: Quote[];
  news: NewsItem[];
}

function formatPrice(price: number): string {
  if (price >= 10000) return price.toLocaleString('en-US', { maximumFractionDigits: 0 });
  if (price >= 1000) return price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  if (price >= 10) return price.toFixed(2);
  return price.toFixed(4);
}

function QuoteRow({ quote }: { quote: Quote }) {
  const up = quote.change >= 0;
  return (
    <div className={styles.quoteRow}>
      <span className={styles.quoteName}>{quote.name}</span>
      <span className={styles.quotePrice}>{formatPrice(quote.price)}</span>
      <span className={up ? styles.quoteUp : styles.quoteDown}>
        {up ? '+' : ''}{quote.change_pct.toFixed(2)}%
      </span>
      <span className={up ? styles.quoteArrowUp : styles.quoteArrowDown}>
        {up ? '▲' : '▼'}
      </span>
    </div>
  );
}

export function MarketsWidget() {
  const [collapsed, toggleCollapsed] = useWidgetCollapse('markets');
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [watchlist, setWatchlist] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newSymbol, setNewSymbol] = useState('');
  const [addingSymbol, setAddingSymbol] = useState(false);

  const fetchSnapshot = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/markets/snapshot`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setSnapshot(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load market data');
    }
    setLoading(false);
  }, []);

  const fetchWatchlist = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/markets/watchlist`);
      const data = await res.json();
      setWatchlist(data.watchlist || []);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    fetchSnapshot();
    fetchWatchlist();
  }, [fetchSnapshot, fetchWatchlist]);

  useEffect(() => {
    const interval = setInterval(fetchSnapshot, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [fetchSnapshot]);

  const addSymbol = async () => {
    const sym = newSymbol.trim().toUpperCase();
    if (!sym) return;
    setAddingSymbol(true);
    try {
      const res = await fetch(`${API_BASE}/markets/watchlist`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol: sym }),
      });
      const data = await res.json();
      setWatchlist(data.watchlist || []);
      setNewSymbol('');
      fetchSnapshot();
    } catch { /* ignore */ }
    setAddingSymbol(false);
  };

  const removeSymbol = async (symbol: string) => {
    try {
      const res = await fetch(`${API_BASE}/markets/watchlist/${encodeURIComponent(symbol)}`, {
        method: 'DELETE',
      });
      const data = await res.json();
      setWatchlist(data.watchlist || []);
      fetchSnapshot();
    } catch { /* ignore */ }
  };

  return (
    <div className={styles.widget}>
      <div className={styles.header}>
        <span className={styles.title}>Markets</span>
        <div className={styles.headerRight}>
          <button className={styles.refreshBtn} onClick={fetchSnapshot} title="Refresh">
            {'\u21BB'}
          </button>
          <button className={styles.collapseBtn} onClick={toggleCollapsed} title={collapsed ? 'Expand' : 'Collapse'}>
            {collapsed ? '\u25B8' : '\u25BE'}
          </button>
        </div>
      </div>

      {!collapsed && (
        loading ? (
          <div className={styles.loadingText}>Loading market data...</div>
        ) : error ? (
          <div className={styles.errorText}>{error}</div>
        ) : snapshot ? (
          <div className={styles.body}>
            {/* Indexes */}
            {snapshot.indexes.length > 0 && (
              <div className={styles.section}>
                <div className={styles.sectionLabel}>Indexes</div>
                {snapshot.indexes.map(q => <QuoteRow key={q.symbol} quote={q} />)}
              </div>
            )}

            {/* Macro */}
            {snapshot.macro.length > 0 && (
              <div className={styles.section}>
                <div className={styles.sectionLabel}>Macro</div>
                {snapshot.macro.map(q => <QuoteRow key={q.symbol} quote={q} />)}
              </div>
            )}

            {/* Watchlist */}
            <div className={styles.section}>
              <div className={styles.sectionHeader}>
                <span className={styles.sectionLabel}>Watchlist</span>
              </div>
              {snapshot.watchlist.map(q => (
                <div key={q.symbol} className={styles.watchlistRow}>
                  <QuoteRow quote={q} />
                  <button
                    className={styles.removeBtn}
                    onClick={() => removeSymbol(q.symbol)}
                    title={`Remove ${q.symbol}`}
                  >
                    {'\u00D7'}
                  </button>
                </div>
              ))}
              <div className={styles.addRow}>
                <input
                  className={styles.symbolInput}
                  type="text"
                  placeholder="Add ticker..."
                  value={newSymbol}
                  onChange={e => setNewSymbol(e.target.value.toUpperCase())}
                  onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addSymbol(); } }}
                  disabled={addingSymbol}
                />
                {newSymbol.trim() && (
                  <button className={styles.addBtn} onClick={addSymbol} disabled={addingSymbol}>
                    {addingSymbol ? '...' : 'Add'}
                  </button>
                )}
              </div>
            </div>

            {/* News */}
            {snapshot.news.length > 0 && (
              <div className={styles.section}>
                <div className={styles.sectionLabel}>Headlines</div>
                <div className={styles.newsList}>
                  {snapshot.news.slice(0, 8).map((item, i) => (
                    <a
                      key={i}
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={styles.newsItem}
                    >
                      <span className={styles.newsSource}>{item.source}</span>
                      <span className={styles.newsTitle}>{item.title}</span>
                    </a>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : null
      )}
    </div>
  );
}
