import { useState, useRef, useCallback } from 'react';
import { API_BASE } from '../services/api';

export type PrivacyLevel = 'public' | 'semi-private' | 'full-private';

export interface WPCategory {
  id: number;
  name: string;
}

export interface UploadedImage {
  file: File;
  preview: string;
}

export function useWordPressCompose() {
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [tags, setTags] = useState('');
  const [selectedCategoryNames, setSelectedCategoryNames] = useState<string[]>([]);
  const [newCategory, setNewCategory] = useState('');
  const [status, setStatus] = useState<'draft' | 'publish'>('draft');
  const [privacy, setPrivacy] = useState<PrivacyLevel>('public');
  const [password, setPassword] = useState('');
  const [images, setImages] = useState<UploadedImage[]>([]);
  const [featuredIdx, setFeaturedIdx] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [availableCategories, setAvailableCategories] = useState<WPCategory[]>([]);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const reset = () => {
    setTitle('');
    setContent('');
    setTags('');
    setSelectedCategoryNames([]);
    setNewCategory('');
    setStatus('draft');
    setPrivacy('public');
    setPassword('');
    setImages(prev => { prev.forEach(img => URL.revokeObjectURL(img.preview)); return []; });
    setFeaturedIdx(null);
  };

  const fetchCategories = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/integrations/wordpress/categories`);
      const data = await res.json();
      if (data.categories) setAvailableCategories(data.categories);
    } catch { /* ignore */ }
  }, []);

  const toggleCategory = (name: string) => {
    setSelectedCategoryNames(prev =>
      prev.includes(name) ? prev.filter(n => n !== name) : [...prev, name]
    );
  };

  const addNewCategory = () => {
    const name = newCategory.trim();
    if (!name) return;
    if (!selectedCategoryNames.includes(name)) {
      setSelectedCategoryNames(prev => [...prev, name]);
    }
    setNewCategory('');
  };

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    const newImages: UploadedImage[] = Array.from(files).map(file => ({
      file,
      preview: URL.createObjectURL(file),
    }));
    setImages(prev => [...prev, ...newImages]);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const removeImage = (idx: number) => {
    setImages(prev => {
      URL.revokeObjectURL(prev[idx].preview);
      return prev.filter((_, i) => i !== idx);
    });
    setFeaturedIdx(prev => {
      if (prev === idx) return null;
      if (prev !== null && prev > idx) return prev - 1;
      return prev;
    });
  };

  const insertImageAtCursor = (url: string) => {
    const tag = `\n<img src="${url}" alt="" />\n`;
    const ta = textareaRef.current;
    if (ta) {
      const start = ta.selectionStart;
      const end = ta.selectionEnd;
      const val = ta.value;
      setContent(val.slice(0, start) + tag + val.slice(end));
    } else {
      setContent(prev => prev + tag);
    }
  };

  const submit = async (onSuccess: () => void): Promise<string | null> => {
    if (!title.trim()) return 'Title is required';
    setSubmitting(true);
    try {
      let featuredMediaId: number | null = null;
      let finalContent = content;

      for (let i = 0; i < images.length; i++) {
        const img = images[i];
        const formData = new FormData();
        formData.append('file', img.file);
        const res = await fetch(`${API_BASE}/integrations/wordpress/media`, {
          method: 'POST',
          body: formData,
        });
        const data = await res.json();
        if (data.error) throw new Error(data.error as string);
        if (!data.media) continue;

        const { id, url } = data.media as { id: number; url: string };
        if (i === featuredIdx) featuredMediaId = id;
        const localTag = `<img src="${img.preview}"`;
        if (finalContent.includes(localTag)) {
          finalContent = finalContent.replace(localTag, `<img src="${url}"`);
        } else if (i !== featuredIdx) {
          finalContent += `\n<img src="${url}" alt="" />\n`;
        }
      }

      const tagList = tags.split(',').map(t => t.trim()).filter(Boolean);
      const body: Record<string, unknown> = {
        title: title.trim(),
        content: finalContent,
        status,
        privacy_level: privacy,
      };
      if (privacy !== 'public' && password.trim()) body.post_password = password.trim();
      if (tagList.length) body.tags = tagList;
      if (selectedCategoryNames.length) body.categories = selectedCategoryNames;
      if (featuredMediaId) body.featured_media = featuredMediaId;

      const res = await fetch(`${API_BASE}/integrations/wordpress/posts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (data.error) {
        setSubmitting(false);
        return data.error as string;
      }
      reset();
      setSubmitting(false);
      onSuccess();
      return null;
    } catch (e) {
      setSubmitting(false);
      return e instanceof Error ? e.message : 'Failed to create post';
    }
  };

  return {
    title, setTitle,
    content, setContent,
    tags, setTags,
    selectedCategoryNames,
    newCategory, setNewCategory,
    status, setStatus,
    privacy, setPrivacy,
    password, setPassword,
    images,
    featuredIdx, setFeaturedIdx,
    submitting,
    availableCategories,
    fileInputRef, textareaRef,
    reset, fetchCategories,
    toggleCategory, addNewCategory,
    handleImageSelect, removeImage, insertImageAtCursor,
    submit,
  };
}
