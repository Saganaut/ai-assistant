import { useState } from 'react';
import styles from './WordPressWidget.module.css';
import { useWidgetCollapse } from '../../hooks/useWidgetCollapse';
import { useWordPressPosts } from '../../hooks/useWordPressPosts';
import type { WPPost, PostFilter } from '../../hooks/useWordPressPosts';
import { useWordPressCompose } from '../../hooks/useWordPressCompose';
import type { PrivacyLevel } from '../../hooks/useWordPressCompose';

type View = 'list' | 'detail' | 'compose';

// --- Helpers ---

function formatDate(iso: string): string {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function statusClass(status: string): string {
  switch (status) {
    case 'publish': return styles.statusPublish;
    case 'draft': return styles.statusDraft;
    case 'pending': return styles.statusPending;
    case 'private': return styles.statusPrivate;
    default: return styles.statusBadge;
  }
}

function PrivacyBadge({ level }: { level?: string }) {
  if (level === 'full-private') return <span className={styles.statusFullPrivate}>full-private</span>;
  if (level === 'semi-private') return <span className={styles.statusSemiPrivate}>semi-private</span>;
  return null;
}

// --- ListView ---

interface ListViewProps {
  posts: WPPost[];
  filter: PostFilter;
  setFilter: (f: PostFilter) => void;
  loading: boolean;
  configured: boolean | null;
  collapsed: boolean;
  onToggleCollapse: () => void;
  onSelectPost: (id: number) => void;
  onRefresh: () => void;
  onNewPost: () => void;
  error: string | null;
}

function ListView({ posts, filter, setFilter, loading, configured, collapsed, onToggleCollapse, onSelectPost, onRefresh, onNewPost, error }: ListViewProps) {
  return (
    <div className={styles.widget}>
      <div className={styles.header}>
        <span className={styles.title}>WordPress</span>
        <div className={styles.headerRight}>
          {configured && (
            <button className={styles.newPostButton} onClick={onNewPost}>+ New Post</button>
          )}
          <button className={styles.navButton} onClick={onRefresh}>{'\u21BB'}</button>
          <button className={styles.navButton} onClick={onToggleCollapse} title={collapsed ? 'Expand' : 'Collapse'}>
            {collapsed ? '\u25B8' : '\u25BE'}
          </button>
        </div>
      </div>

      {!collapsed && (
        loading ? (
          <div className={styles.helpText}>Loading...</div>
        ) : !configured ? (
          <p className={styles.helpText}>
            Set ASSISTANT_WORDPRESS_URL, ASSISTANT_WORDPRESS_USERNAME, and
            ASSISTANT_WORDPRESS_APP_PASSWORD in your .env file.
          </p>
        ) : (
          <>
            <div className={styles.tabs}>
              <button className={filter === 'any' ? styles.tabActive : styles.tab} onClick={() => setFilter('any')}>All</button>
              <button className={filter === 'draft' ? styles.tabActive : styles.tab} onClick={() => setFilter('draft')}>Drafts</button>
            </div>

            {error && <p className={styles.errorText}>{error}</p>}

            {posts.length > 0 ? (
              <div className={styles.postList}>
                {posts.map(post => (
                  <button key={post.id} className={styles.postCard} onClick={() => onSelectPost(post.id)}>
                    <div className={styles.postCardHeader}>
                      <span className={styles.postTitle}>{post.title}</span>
                      <div className={styles.badgeGroup}>
                        <PrivacyBadge level={post.privacy_level} />
                        <span className={statusClass(post.status)}>{post.status}</span>
                      </div>
                    </div>
                    <span className={styles.postDate}>{formatDate(post.date)}</span>
                    <div className={styles.postActions} onClick={e => e.stopPropagation()}>
                      {post.url && (
                        <a href={post.url} target="_blank" rel="noopener noreferrer" className={styles.actionLink}>View</a>
                      )}
                      {post.url && (
                        <a
                          href={new URL(`/wp-admin/post.php?post=${post.id}&action=edit`, post.url).href}
                          target="_blank"
                          rel="noopener noreferrer"
                          className={styles.actionLink}
                        >
                          Edit
                        </a>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <div className={styles.helpText}>No posts found.</div>
            )}
          </>
        )
      )}
    </div>
  );
}

// --- DetailView ---

interface DetailViewProps {
  post: WPPost;
  collapsed: boolean;
  onToggleCollapse: () => void;
  onBack: () => void;
  publishing: boolean;
  onPublish: () => void;
  error: string | null;
}

function DetailView({ post, collapsed, onToggleCollapse, onBack, publishing, onPublish, error }: DetailViewProps) {
  const contentPreview = post.content.length > 500
    ? post.content.slice(0, 500) + '...'
    : post.content;

  return (
    <div className={styles.widget}>
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <button className={styles.navButton} onClick={onBack}>{'\u2039'}</button>
          <span className={styles.title}>Post #{post.id}</span>
        </div>
        <div className={styles.headerRight}>
          {post.url && (
            <a href={post.url} target="_blank" rel="noopener noreferrer" className={styles.externalLink}>
              Open in WP
            </a>
          )}
          <button className={styles.navButton} onClick={onToggleCollapse} title={collapsed ? 'Expand' : 'Collapse'}>
            {collapsed ? '\u25B8' : '\u25BE'}
          </button>
        </div>
      </div>

      {!collapsed && (
        <div className={styles.detail}>
          <div className={styles.detailTitle}>{post.title}</div>
          <div className={styles.detailMeta}>
            <span className={statusClass(post.status)}>{post.status}</span>
            <PrivacyBadge level={post.privacy_level} />
            <span className={styles.detailDate}>{formatDate(post.date)}</span>
          </div>
          {post.excerpt && <div className={styles.detailExcerpt}>{post.excerpt}</div>}
          {contentPreview && <div className={styles.detailContent}>{contentPreview}</div>}
          {post.tags.length > 0 && (
            <div className={styles.detailField}>
              <span className={styles.detailFieldLabel}>Tags</span>
              <div className={styles.chips}>
                {post.tags.map(t => <span key={t} className={styles.chip}>#{t}</span>)}
              </div>
            </div>
          )}
          {post.categories.length > 0 && (
            <div className={styles.detailField}>
              <span className={styles.detailFieldLabel}>Categories</span>
              <div className={styles.chips}>
                {post.categories.map(c => <span key={c} className={styles.chip}>#{c}</span>)}
              </div>
            </div>
          )}
          {error && <p className={styles.errorText}>{error}</p>}
          {post.status === 'draft' && (
            <button className={styles.publishButton} onClick={onPublish} disabled={publishing}>
              {publishing ? 'Publishing...' : 'Publish'}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// --- ComposeView ---

type ComposeHook = ReturnType<typeof useWordPressCompose>;

interface ComposeViewProps {
  compose: ComposeHook;
  collapsed: boolean;
  onToggleCollapse: () => void;
  onBack: () => void;
  onSuccess: () => void;
  onError: (msg: string) => void;
  error: string | null;
}

function ComposeView({ compose, collapsed, onToggleCollapse, onBack, onSuccess, onError, error }: ComposeViewProps) {
  const handleSubmit = async () => {
    const err = await compose.submit(onSuccess);
    if (err) onError(err);
  };

  const newCategories = compose.selectedCategoryNames.filter(
    n => !compose.availableCategories.some(c => c.name === n)
  );

  return (
    <div className={styles.widget}>
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <button className={styles.navButton} onClick={onBack}>{'\u2039'}</button>
          <span className={styles.title}>New Post</span>
        </div>
        <button className={styles.navButton} onClick={onToggleCollapse} title={collapsed ? 'Expand' : 'Collapse'}>
          {collapsed ? '\u25B8' : '\u25BE'}
        </button>
      </div>

      {!collapsed && (
        <div className={styles.composeForm}>
          <input
            className={styles.composeInput}
            type="text"
            placeholder="Post title"
            value={compose.title}
            onChange={e => compose.setTitle(e.target.value)}
          />

          <div className={styles.textareaWrap}>
            <textarea
              ref={compose.textareaRef}
              className={styles.composeTextarea}
              placeholder="Write your post content (HTML supported)..."
              value={compose.content}
              onChange={e => compose.setContent(e.target.value)}
              rows={8}
            />
            <span className={styles.textareaHint}>HTML tags like &lt;p&gt;, &lt;h2&gt;, &lt;img&gt;, &lt;a&gt; are supported</span>
          </div>

          <input
            className={styles.composeInput}
            type="text"
            placeholder="Tags (comma-separated)"
            value={compose.tags}
            onChange={e => compose.setTags(e.target.value)}
          />

          {/* Categories */}
          <div className={styles.composeFieldGroup}>
            <span className={styles.composeLabel}>Categories</span>
            {compose.availableCategories.length > 0 && (
              <div className={styles.categoryChips}>
                {compose.availableCategories.map(cat => (
                  <button
                    key={cat.id}
                    className={compose.selectedCategoryNames.includes(cat.name) ? styles.categoryChipActive : styles.categoryChip}
                    onClick={() => compose.toggleCategory(cat.name)}
                  >
                    {cat.name}
                  </button>
                ))}
              </div>
            )}
            <div className={styles.addCategoryRow}>
              <input
                className={styles.composeInputSmall}
                type="text"
                placeholder="New category..."
                value={compose.newCategory}
                onChange={e => compose.setNewCategory(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); compose.addNewCategory(); } }}
              />
              {compose.newCategory.trim() && (
                <button className={styles.addCategoryBtn} onClick={compose.addNewCategory}>Add</button>
              )}
            </div>
            {newCategories.length > 0 && (
              <div className={styles.categoryChips}>
                {newCategories.map(name => (
                  <button key={name} className={styles.categoryChipActive} onClick={() => compose.toggleCategory(name)}>
                    {name} (new)
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Images */}
          <div className={styles.composeFieldGroup}>
            <span className={styles.composeLabel}>Images</span>
            <input
              ref={compose.fileInputRef}
              type="file"
              accept="image/*"
              multiple
              onChange={compose.handleImageSelect}
              className={styles.composeFileInput}
            />
            {compose.images.length > 0 && (
              <div className={styles.imageGrid}>
                {compose.images.map((img, idx) => (
                  <div key={idx} className={styles.imagePreviewWrap}>
                    <img src={img.preview} alt="Preview" className={styles.imagePreview} />
                    <button className={styles.removeImageBtn} onClick={() => compose.removeImage(idx)}>&times;</button>
                    <div className={styles.imageActions}>
                      <button
                        className={compose.featuredIdx === idx ? styles.featuredBtnActive : styles.featuredBtn}
                        onClick={() => compose.setFeaturedIdx(compose.featuredIdx === idx ? null : idx)}
                        title="Set as featured image"
                      >
                        {compose.featuredIdx === idx ? 'Featured' : 'Set featured'}
                      </button>
                      <button
                        className={styles.insertBtn}
                        onClick={() => compose.insertImageAtCursor(img.preview)}
                        title="Insert into content"
                      >
                        Insert
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Privacy */}
          <div className={styles.composeFieldGroup}>
            <span className={styles.composeLabel}>Privacy</span>
            <div className={styles.privacyRow}>
              <select
                className={styles.privacySelect}
                value={compose.privacy}
                onChange={e => compose.setPrivacy(e.target.value as PrivacyLevel)}
              >
                <option value="public">Public</option>
                <option value="semi-private">Semi-Private (images hidden)</option>
                <option value="full-private">Full-Private (all content hidden)</option>
              </select>
              {compose.privacy !== 'public' && (
                <input
                  className={styles.composeInputSmall}
                  type="password"
                  placeholder="Password (blank = site default)"
                  value={compose.password}
                  onChange={e => compose.setPassword(e.target.value)}
                />
              )}
            </div>
          </div>

          <div className={styles.composeFooter}>
            <div className={styles.statusToggle}>
              <button
                className={compose.status === 'draft' ? styles.tabActive : styles.tab}
                onClick={() => compose.setStatus('draft')}
              >
                Draft
              </button>
              <button
                className={compose.status === 'publish' ? styles.tabActive : styles.tab}
                onClick={() => compose.setStatus('publish')}
              >
                Publish
              </button>
            </div>
            <button
              className={styles.publishButton}
              onClick={handleSubmit}
              disabled={compose.submitting || !compose.title.trim()}
            >
              {compose.submitting ? 'Creating...' : 'Create Post'}
            </button>
          </div>

          {error && <p className={styles.errorText}>{error}</p>}
        </div>
      )}
    </div>
  );
}

// --- WordPressWidget (orchestrator) ---

export function WordPressWidget() {
  const [collapsed, toggleCollapsed] = useWidgetCollapse('wordpress');
  const [view, setView] = useState<View>('list');
  const [composeError, setComposeError] = useState<string | null>(null);

  const postsHook = useWordPressPosts();
  const compose = useWordPressCompose();

  const openCompose = () => {
    compose.reset();
    compose.fetchCategories();
    setComposeError(null);
    setView('compose');
  };

  const goToList = () => {
    postsHook.setSelectedPost(null);
    postsHook.setError(null);
    setView('list');
  };

  const handleSelectPost = async (id: number) => {
    const ok = await postsHook.fetchPostDetail(id);
    if (ok) setView('detail');
  };

  const handleComposeSuccess = () => {
    postsHook.fetchPosts(postsHook.filter);
    setView('list');
  };

  if (view === 'compose') {
    return (
      <ComposeView
        compose={compose}
        collapsed={collapsed}
        onToggleCollapse={toggleCollapsed}
        onBack={() => { compose.reset(); goToList(); }}
        onSuccess={handleComposeSuccess}
        onError={setComposeError}
        error={composeError}
      />
    );
  }

  if (view === 'detail' && postsHook.selectedPost) {
    return (
      <DetailView
        post={postsHook.selectedPost}
        collapsed={collapsed}
        onToggleCollapse={toggleCollapsed}
        onBack={goToList}
        publishing={postsHook.publishing}
        onPublish={() => postsHook.publishPost(postsHook.selectedPost!.id)}
        error={postsHook.error}
      />
    );
  }

  return (
    <ListView
      posts={postsHook.posts}
      filter={postsHook.filter}
      setFilter={postsHook.setFilter}
      loading={postsHook.loading}
      configured={postsHook.configured}
      collapsed={collapsed}
      onToggleCollapse={toggleCollapsed}
      onSelectPost={handleSelectPost}
      onRefresh={() => postsHook.fetchPosts(postsHook.filter)}
      onNewPost={openCompose}
      error={postsHook.error}
    />
  );
}
