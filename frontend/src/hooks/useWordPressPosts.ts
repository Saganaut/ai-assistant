import { useState, useEffect, useCallback } from 'react';
import { API_BASE } from '../services/api';

export interface WPPost {
  id: number;
  title: string;
  status: string;
  date: string;
  url: string;
  excerpt: string;
  content: string;
  tags: number[];
  categories: number[];
  privacy_level: 'public' | 'semi-private' | 'full-private';
}

export type PostFilter = 'any' | 'draft';

export function useWordPressPosts() {
  const [configured, setConfigured] = useState<boolean | null>(null);
  const [posts, setPosts] = useState<WPPost[]>([]);
  const [selectedPost, setSelectedPost] = useState<WPPost | null>(null);
  const [filter, setFilter] = useState<PostFilter>('any');
  const [loading, setLoading] = useState(true);
  const [publishing, setPublishing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPosts = useCallback(async (statusFilter: string = 'any') => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ status: statusFilter, per_page: '20' });
      const res = await fetch(`${API_BASE}/integrations/wordpress/posts?${params}`);
      const data = await res.json();
      setConfigured(data.configured);
      if (data.error) setError(data.error);
      else setPosts(data.posts || []);
    } catch {
      setConfigured(false);
    }
    setLoading(false);
  }, []);

  const fetchPostDetail = useCallback(async (postId: number): Promise<boolean> => {
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/integrations/wordpress/posts/${postId}`);
      const data = await res.json();
      if (data.error) { setError(data.error); return false; }
      if (data.post) { setSelectedPost(data.post); return true; }
      return false;
    } catch {
      setError('Failed to load post');
      return false;
    }
  }, []);

  const publishPost = useCallback(async (postId: number) => {
    setPublishing(true);
    try {
      const res = await fetch(`${API_BASE}/integrations/wordpress/posts/${postId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'publish' }),
      });
      const data = await res.json();
      if (data.error) setError(data.error);
      else if (data.post) {
        setSelectedPost(data.post);
        fetchPosts(filter);
      }
    } catch {
      setError('Failed to publish post');
    }
    setPublishing(false);
  }, [fetchPosts, filter]);

  useEffect(() => { fetchPosts(filter); }, [fetchPosts, filter]);

  useEffect(() => {
    const id = setInterval(() => fetchPosts(filter), 5 * 60 * 1000);
    return () => clearInterval(id);
  }, [fetchPosts, filter]);

  return {
    configured, posts, selectedPost, setSelectedPost,
    filter, setFilter,
    loading, publishing, error, setError,
    fetchPosts, fetchPostDetail, publishPost,
  };
}
