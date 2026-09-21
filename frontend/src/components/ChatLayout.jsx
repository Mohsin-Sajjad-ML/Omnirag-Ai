import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useReducedMotion } from 'motion/react';
import { UploadCloud } from 'lucide-react';

import { useAuth } from '../context/AuthContext';
import { useClerk, useUser } from '@clerk/clerk-react';
import api from '../services/api';

import ChatSidebar from './chat/ChatSidebar';
import ChatChatMessageList from './chat/ChatMessageList';
import ChatInputBar from './chat/ChatInputBar';
import ChatSettingsModal from './chat/ChatSettingsModal';

export const ChatLayout = () => {
  const osReducedMotion = useReducedMotion();
  const [manualReduceMotion, setManualReduceMotion] = useState(() => {
    return localStorage.getItem('omnirag_reduce_motion') === 'true';
  });
  const shouldReduceMotion = Boolean(osReducedMotion || manualReduceMotion);

  const toggleManualReduceMotion = () => {
    setManualReduceMotion((prev) => {
      const next = !prev;
      localStorage.setItem('omnirag_reduce_motion', String(next));
      return next;
    });
  };

  const { user, loginMethod, logout } = useAuth();
  const navigate = useNavigate();
  const { signOut } = useClerk();
  const { user: clerkUser } = useUser();

  // Collapsible sidebar state (persisted in localStorage)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    return localStorage.getItem('omnirag_sidebar_collapsed') === 'true';
  });
  const [collapsedSearchOpen, setCollapsedSearchOpen] = useState(false);

  // Settings modal state
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settingsTab, setSettingsTab] = useState('appearance');

  // Account deletion confirmation dialog state
  const [deleteAccountModalOpen, setDeleteAccountModalOpen] = useState(false);
  const [deleteAccountInput, setDeleteAccountInput] = useState('');
  const [isDeletingAccount, setIsDeletingAccount] = useState(false);
  const [deleteAccountError, setDeleteAccountError] = useState('');

  // Clear all chats confirmation dialog state
  const [clearChatsModalOpen, setClearChatsModalOpen] = useState(false);
  const [clearChatsInput, setClearChatsInput] = useState('');
  const [isClearingChats, setIsClearingChats] = useState(false);

  // Default toggles for new conversations (persisted in localStorage)
  const [defaultRagEnabled, setDefaultRagEnabled] = useState(() => {
    const val = localStorage.getItem('omnirag_default_rag');
    return val !== null ? val === 'true' : true;
  });
  const [defaultWebSearchEnabled, setDefaultWebSearchEnabled] = useState(() => {
    const val = localStorage.getItem('omnirag_default_web');
    return val !== null ? val === 'true' : false;
  });

  const updateDefaultRag = (val) => {
    setDefaultRagEnabled(val);
    localStorage.setItem('omnirag_default_rag', String(val));
  };

  const updateDefaultWeb = (val) => {
    setDefaultWebSearchEnabled(val);
    localStorage.setItem('omnirag_default_web', String(val));
  };

  // Active chat session toggles
  const [ragEnabled, setRagEnabled] = useState(defaultRagEnabled);
  const [webSearchEnabled, setWebSearchEnabled] = useState(defaultWebSearchEnabled);

  // Sidebar mobile drawer state
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // User menu dropdown in top right
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  // Personalized welcome banner at top of chat area
  const [showWelcomeBanner, setShowWelcomeBanner] = useState(true);

  // Sessions state
  const [sessions, setSessions] = useState([]);
  const [sessionSearch, setSessionSearch] = useState('');
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [loadingSessions, setLoadingSessions] = useState(true);

  // Filtered sessions based on search bar query
  const filteredSessions = useMemo(() => {
    if (!sessionSearch.trim()) return sessions;
    const q = sessionSearch.toLowerCase().trim();
    return sessions.filter((s) => (s.title || '').toLowerCase().includes(q));
  }, [sessions, sessionSearch]);

  const [activeContextMenu, setActiveContextMenu] = useState(null);
  const [isUndoDeleting, setIsUndoDeleting] = useState(false);
  const [undoSessionData, setUndoSessionData] = useState(null);
  const deleteTimeoutRef = useRef(null);
  const [editingMessageId, setEditingMessageId] = useState(null);
  const [editingMessageContent, setEditingMessageContent] = useState('');
  const [editingSessionId, setEditingSessionId] = useState(null);
  const [editingTitle, setEditingTitle] = useState('');
  const [showUploadMenu, setShowUploadMenu] = useState(false);
  const uploadMenuRef = useRef(null);

  // Active citation for popup modal with layoutId
  const [activeCitation, setActiveCitation] = useState(null);

  // Messages state for active session
  const [messages, setMessages] = useState([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [isSending, setIsSending] = useState(false);

  // User input text
  const [inputQuery, setInputQuery] = useState('');

  // Documents state for document scope selector
  const [documents, setDocuments] = useState([]);
  const [selectedDocIds, setSelectedDocIds] = useState([]);
  const [docSelectorOpen, setDocSelectorOpen] = useState(false);
  const [docSearchQuery, setDocSearchQuery] = useState('');

  const filteredScopeDocuments = useMemo(() => {
    if (!docSearchQuery.trim()) return documents;
    const q = docSearchQuery.toLowerCase().trim();
    return documents.filter((doc) =>
      (doc.original_filename || '').toLowerCase().includes(q)
    );
  }, [documents, docSearchQuery]);

  // Inline system notifications (e.g. uploads in progress/completed)
  const [inlineEvents, setInlineEvents] = useState([]);

  // References
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const docSelectorRef = useRef(null);
  const userMenuRef = useRef(null);

  const ALLOWED_EXTENSIONS = ['pdf', 'docx', 'txt', 'csv'];
  const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB

  const uploadMenuItems = [
    {
      id: 'upload-document',
      label: 'Upload a document',
      icon: UploadCloud,
      action: () => fileInputRef.current?.click(),
    },
  ];

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  const handleRevealComplete = useCallback((msgId) => {
    setMessages((prev) =>
      prev.map((m) => (m.id === msgId ? { ...m, animateReveal: false } : m))
    );
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, inlineEvents, isSending, scrollToBottom]);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (
        activeContextMenu &&
        !e.target.closest('.session-context-menu-container') &&
        !e.target.closest('.session-context-trigger')
      ) {
        setActiveContextMenu(null);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [activeContextMenu]);

  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const recordingChunksRef = audioChunksRef;
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const animFrameRef = useRef(null);
  const isCancelledRef = useRef(false);
  const isRecordingCancelledRef = isCancelledRef;
  const [audioLevels, setAudioLevels] = useState([6, 12, 18, 12, 6]);

  // Language-aware speech synthesis
  const handleReadAloud = useCallback((content, responseLanguage) => {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(content);
    const voices = window.speechSynthesis.getVoices();
    if (responseLanguage === 'roman-ur') {
      const urduVoice = voices.find(
        (v) => v.lang.toLowerCase().startsWith('ur') || v.lang.includes('ur-PK')
      );
      if (urduVoice) {
        utterance.voice = urduVoice;
      } else {
        utterance.lang = 'ur-PK';
      }
    } else {
      const engVoice = voices.find((v) => v.lang.toLowerCase().startsWith('en'));
      if (engVoice) {
        utterance.voice = engVoice;
      } else {
        utterance.lang = 'en-US';
      }
    }
    window.speechSynthesis.speak(utterance);
  }, []);

  const startVoiceRecording = async () => {
    try {
      isCancelledRef.current = false;
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      try {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (AudioCtx) {
          const audioCtx = new AudioCtx();
          audioContextRef.current = audioCtx;
          const source = audioCtx.createMediaStreamSource(stream);
          const analyser = audioCtx.createAnalyser();
          analyser.fftSize = 64;
          source.connect(analyser);
          analyserRef.current = analyser;

          const dataArray = new Uint8Array(analyser.frequencyBinCount);
          const sampleAudio = () => {
            if (!analyserRef.current) return;
            analyserRef.current.getByteFrequencyData(dataArray);
            const b0 = Math.max(4, Math.round((dataArray[1] / 255) * 18));
            const b1 = Math.max(4, Math.round((dataArray[3] / 255) * 22));
            const b2 = Math.max(4, Math.round((dataArray[6] / 255) * 24));
            const b3 = Math.max(4, Math.round((dataArray[9] / 255) * 22));
            const b4 = Math.max(4, Math.round((dataArray[12] / 255) * 18));
            setAudioLevels([b0, b1, b2, b3, b4]);
            animFrameRef.current = requestAnimationFrame(sampleAudio);
          };
          sampleAudio();
        }
      } catch (audioErr) {
        console.warn('AudioContext setup skipped or unsupported:', audioErr);
      }

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = async () => {
        if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
        if (audioContextRef.current) {
          audioContextRef.current.close().catch(() => {});
          audioContextRef.current = null;
        }
        analyserRef.current = null;
        stream.getTracks().forEach((t) => t.stop());

        if (isCancelledRef.current) {
          isCancelledRef.current = false;
          audioChunksRef.current = [];
          return;
        }

        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        audioChunksRef.current = [];
        if (audioBlob.size > 0) {
          const formData = new FormData();
          formData.append('audio', audioBlob, 'recording.webm');
          setIsTranscribing(true);
          try {
            const res = await api.post('/chat/transcribe', formData, {
              headers: { 'Content-Type': 'multipart/form-data' },
            });
            const transcribed = (res.data?.transcript || res.data?.text || '').trim();
            if (transcribed) {
              setInputQuery(transcribed);
              await handleSendMessage(null, transcribed);
            }
          } catch (err) {
            console.error('Transcription error:', err);
          } finally {
            setIsTranscribing(false);
          }
        }
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (err) {
      console.error('Microphone error:', err);
    }
  };

  const stopVoiceRecording = () => {
    isCancelledRef.current = false;
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
    analyserRef.current = null;
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  // Distinct Stop & Send vs Cancel & Discard controls
  // "Stop and send voice recording", "Cancel and discard recording", "Rec"
  const handleCancelRecording = () => {
    isCancelledRef.current = true;
    isRecordingCancelledRef.current = true;
    recordingChunksRef.current = [];
    audioChunksRef.current = [];
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
    analyserRef.current = null;
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const cancelVoiceRecording = handleCancelRecording;

  const toggleVoiceRecording = () => {
    if (isRecording) {
      stopVoiceRecording();
    } else {
      startVoiceRecording();
    }
  };

  useEffect(() => {
    function handleClickOutside(e) {
      if (docSelectorRef.current && !docSelectorRef.current.contains(e.target)) {
        setDocSelectorOpen(false);
      }
      if (userMenuRef.current && !userMenuRef.current.contains(e.target)) {
        setUserMenuOpen(false);
      }
      if (uploadMenuRef.current && !uploadMenuRef.current.contains(e.target)) {
        setShowUploadMenu(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      setShowWelcomeBanner(false);
    }, 8000);
    return () => clearTimeout(timer);
  }, [user]);

  const fetchUserDocuments = async () => {
    if (!user) return;
    try {
      const res = await api.get(`/documents/${encodeURIComponent(user)}`);
      setDocuments(res.data || []);
    } catch (err) {
      console.error('Error fetching user documents:', err);
    }
  };

  useEffect(() => {
    let isCurrent = true;

    setSessions([]);
    setActiveSessionId(null);
    setMessages([]);
    setDocuments([]);
    setSelectedDocIds([]);
    setInlineEvents([]);
    setInputQuery('');
    setUserMenuOpen(false);
    setDocSelectorOpen(false);
    setShowWelcomeBanner(true);

    if (!user) return;

    const loadDocs = async () => {
      try {
        const res = await api.get(`/documents/${encodeURIComponent(user)}`);
        if (isCurrent) {
          setDocuments(res.data || []);
        }
      } catch (err) {
        if (isCurrent) {
          console.error('Error fetching user documents:', err);
        }
      }
    };
    loadDocs();

    const initSessions = async () => {
      setLoadingSessions(true);
      try {
        const res = await api.get(`/chat/sessions/${encodeURIComponent(user)}`);
        if (!isCurrent) return;
        const sessionList = res.data || [];
        setSessions(sessionList);

        if (sessionList.length > 0) {
          const mostRecentId = sessionList[0].id || sessionList[0].session_id;
          setActiveSessionId(mostRecentId);
          loadSessionMessages(mostRecentId);
        } else {
          setActiveSessionId(null);
          setMessages([]);
        }
      } catch (err) {
        if (isCurrent) {
          console.error('Error loading sessions on login/mount:', err);
        }
      } finally {
        if (isCurrent) {
          setLoadingSessions(false);
        }
      }
    };

    initSessions();

    return () => {
      isCurrent = false;
    };
  }, [user]);

  const loadSessionMessages = async (sessionId) => {
    if (!sessionId) return;
    setLoadingMessages(true);
    setInlineEvents([]);
    try {
      const res = await api.get(`/chat/sessions/${sessionId}/messages`);
      setMessages(res.data || []);
    } catch (err) {
      console.error('Error loading session messages:', err);
    } finally {
      setLoadingMessages(false);
    }
  };

  const handleSelectSession = (sessionId) => {
    if (sessionId === activeSessionId) return;
    setActiveSessionId(sessionId);
    setSidebarOpen(false);
    setCollapsedSearchOpen(false);
    loadSessionMessages(sessionId);
  };

  const handleCreateNewSession = async () => {
    try {
      const res = await api.post('/chat/sessions', { username: user });
      const newSession = res.data;
      const formatted = {
        id: newSession.session_id || newSession.id,
        session_id: newSession.session_id || newSession.id,
        title: newSession.title || 'New Chat',
        created_at: newSession.created_at,
        pinned: false,
      };

      setSessions((prev) => [formatted, ...prev]);
      setActiveSessionId(formatted.id);
      setMessages([]);
      setInlineEvents([]);
      setInputQuery('');
      setSidebarOpen(false);
      setCollapsedSearchOpen(false);

      setRagEnabled(defaultRagEnabled);
      setWebSearchEnabled(defaultWebSearchEnabled);
    } catch (err) {
      console.error('Error creating new session:', err);
    }
  };

  const handleStartRenameSession = (e, sess) => {
    e.stopPropagation();
    setEditingSessionId(sess.id);
    setEditingTitle(sess.title || 'New Chat');
  };

  const handleSaveSessionTitle = async (sessionId, oldTitle) => {
    const trimmed = editingTitle.trim();
    setEditingSessionId(null);

    if (!trimmed || trimmed === oldTitle) {
      return;
    }

    setSessions((prev) =>
      prev.map((s) => (s.id === sessionId ? { ...s, title: trimmed } : s))
    );

    try {
      await api.patch(`/chat/sessions/${sessionId}`, { title: trimmed });
    } catch (err) {
      console.error('Error renaming session:', err);
      setSessions((prev) =>
        prev.map((s) => (s.id === sessionId ? { ...s, title: oldTitle } : s))
      );
    }
  };

  const handleTogglePinSession = async (sessionId, shouldPin) => {
    setActiveContextMenu(null);
    setSessions((prev) => {
      const updated = prev.map((s) => (s.id === sessionId ? { ...s, pinned: shouldPin } : s));
      return updated.sort((a, b) => {
        if (a.pinned && !b.pinned) return -1;
        if (!a.pinned && b.pinned) return 1;
        return new Date(b.created_at || 0) - new Date(a.created_at || 0);
      });
    });

    try {
      await api.patch(`/chat/sessions/${sessionId}/pin`, { pinned: shouldPin });
    } catch (err) {
      console.error('Error toggling pin status:', err);
    }
  };

  const handleInitiateDeleteSession = (sess) => {
    setActiveContextMenu(null);
    if (deleteTimeoutRef.current) {
      clearTimeout(deleteTimeoutRef.current);
    }

    const sessIndex = sessions.findIndex((s) => s.id === sess.id);
    const targetId = sess.id;
    const remaining = sessions.filter((s) => s.id !== targetId);

    setUndoSessionData({ session: sess, index: sessIndex });
    setIsUndoDeleting(true);
    setSessions(remaining);

    if (activeSessionId === targetId) {
      if (remaining.length > 0) {
        const nextId = remaining[0].id;
        setActiveSessionId(nextId);
        loadSessionMessages(nextId);
      } else {
        setActiveSessionId(null);
        setMessages([]);
      }
    }

    deleteTimeoutRef.current = setTimeout(async () => {
      try {
        await api.delete(`/chat/sessions/${targetId}`);
      } catch (err) {
        console.error('Error deleting session on server:', err);
      } finally {
        setIsUndoDeleting(false);
        setUndoSessionData(null);
      }
    }, 5000);
  };

  const handleUndoDelete = () => {
    if (deleteTimeoutRef.current) {
      clearTimeout(deleteTimeoutRef.current);
    }
    if (!undoSessionData) return;

    const { session, index } = undoSessionData;
    setSessions((prev) => {
      const next = [...prev];
      next.splice(index, 0, session);
      return next;
    });

    setActiveSessionId(session.id);
    loadSessionMessages(session.id);

    setIsUndoDeleting(false);
    setUndoSessionData(null);
  };

  const handleExportSession = async (sessionId, format, mode = 'full', sessionTitle = 'chat') => {
    setActiveContextMenu(null);
    try {
      const response = await api.get(`/chat/sessions/${sessionId}/export`, {
        params: { format, mode },
        responseType: 'blob',
      });

      const blob = new Blob([response.data], {
        type: format === 'pdf' ? 'application/pdf' : 'text/plain; charset=utf-8',
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      const safeTitle = (sessionTitle || 'chat').replace(/[^a-zA-Z0-9_-]/g, '_').slice(0, 30);
      const suffix = mode === 'context' ? '_context' : '';
      link.download = `${safeTitle}${suffix}.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Error exporting session:', err);
      alert('Failed to export session. Please try again.');
    }
  };

  const handleDuplicateSession = async (sessionId) => {
    setActiveContextMenu(null);
    try {
      const res = await api.post(`/chat/sessions/${sessionId}/duplicate`);
      const newSession = res.data;
      const formatted = {
        id: newSession.session_id || newSession.id,
        session_id: newSession.session_id || newSession.id,
        title: newSession.title,
        created_at: newSession.created_at,
        pinned: false,
      };

      setSessions((prev) => [formatted, ...prev]);
      setActiveSessionId(formatted.id);
      loadSessionMessages(formatted.id);
    } catch (err) {
      console.error('Error duplicating session:', err);
      alert('Failed to duplicate session. Please try again.');
    }
  };

  const handleLogout = async () => {
    try {
      if (signOut) {
        await signOut();
      }
      logout();
      navigate('/');
    } catch (err) {
      console.error('Error during logout:', err);
      logout();
      navigate('/');
    }
  };

  const handleSendMessage = async (e, overrideQuery = null) => {
    e?.preventDefault();
    const trimmed = (overrideQuery !== null ? overrideQuery : inputQuery).trim();
    if (!trimmed || isSending) return;

    let targetSessionId = activeSessionId;

    if (!targetSessionId) {
      try {
        const createRes = await api.post('/chat/sessions', { username: user });
        const newSession = createRes.data;
        targetSessionId = newSession.session_id || newSession.id;

        const formatted = {
          id: targetSessionId,
          session_id: targetSessionId,
          title: newSession.title || 'New Chat',
          created_at: newSession.created_at,
        };

        setSessions([formatted]);
        setActiveSessionId(targetSessionId);
      } catch (createErr) {
        console.error('Error creating initial session on send:', createErr);
        setMessages([
          {
            id: `temp-${Date.now()}`,
            role: 'user',
            content: trimmed,
            created_at: new Date().toISOString(),
          },
          {
            id: `err-${Date.now()}`,
            role: 'assistant',
            content: 'Connection error: Unable to connect to the OmniRAG server. Please verify the backend is running and try again.',
            is_error: true,
            created_at: new Date().toISOString(),
          },
        ]);
        setInputQuery('');
        return;
      }
    }

    const optimisticUserMsg = {
      id: `temp-${Date.now()}`,
      session_id: targetSessionId,
      role: 'user',
      content: trimmed,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, optimisticUserMsg]);
    setInputQuery('');
    setIsSending(true);

    try {
      const payload = {
        username: user,
        query: trimmed,
        document_ids: selectedDocIds.length > 0 ? selectedDocIds : null,
        rag_enabled: ragEnabled,
        web_search_enabled: webSearchEnabled,
      };

      const res = await api.post(`/chat/sessions/${targetSessionId}/message`, payload);
      const data = res.data;

      const assistantMsg = {
        id: `resp-${Date.now()}`,
        session_id: targetSessionId,
        role: 'assistant',
        content: data.answer,
        citations: data.citations || [],
        is_fallback: data.is_fallback || false,
        low_context: data.low_context || false,
        source: data.source || (data.citations?.length ? 'rag' : 'llm_api'),
        created_at: new Date().toISOString(),
        animateReveal: true,
      };

      setMessages((prev) => [...prev, assistantMsg]);

      setSessions((prev) =>
        prev.map((s) => {
          if (s.id === targetSessionId && s.title === 'New Chat') {
            const shortTitle = trimmed.length > 40 ? trimmed.substring(0, 37) + '...' : trimmed;
            return { ...s, title: shortTitle };
          }
          return s;
        })
      );
    } catch (err) {
      console.error('Error sending message:', err);
      const isNetworkError =
        !err.response || err.code === 'ERR_NETWORK' || err.message?.includes('Network Error');
      const errContent = isNetworkError
        ? 'Connection error: Unable to connect to the OmniRAG server. Please verify the backend is running and try again.'
        : (err.response?.data?.detail || err.response?.data?.message || 'An error occurred while generating a response. Please try again.');
      const errMsg = {
        id: `err-${Date.now()}`,
        session_id: targetSessionId,
        role: 'assistant',
        content: errContent,
        is_error: true,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setIsSending(false);
    }
  };

  const handleEditUserMessage = async (messageId) => {
    const newContent = editingMessageContent.trim();
    if (!newContent || !activeSessionId || isSending) return;
    setEditingMessageId(null);
    setIsSending(true);

    const targetIdx = messages.findIndex((m) => m.id === messageId);
    if (targetIdx !== -1) {
      setMessages((prev) => {
        const truncated = prev.slice(0, targetIdx + 1);
        truncated[targetIdx] = { ...truncated[targetIdx], content: newContent };
        return truncated;
      });
    }

    try {
      const res = await api.post(`/chat/sessions/${activeSessionId}/messages/${messageId}/edit`, {
        query: newContent,
        rag_enabled: ragEnabled,
        web_search_enabled: webSearchEnabled,
      });
      const data = res.data;
      const assistantMsg = {
        id: `resp-${Date.now()}`,
        session_id: activeSessionId,
        role: 'assistant',
        content: data.answer,
        citations: data.citations || [],
        is_fallback: data.is_fallback || false,
        low_context: data.low_context || false,
        source: data.source || (data.citations?.length ? 'rag' : 'llm_api'),
        created_at: new Date().toISOString(),
        animateReveal: true,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      console.error('Error editing message:', err);
      const errMsg = {
        id: `err-${Date.now()}`,
        session_id: activeSessionId,
        role: 'assistant',
        content: err.response?.data?.detail || 'Failed to edit message and regenerate answer. Please try again.',
        is_error: true,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setIsSending(false);
    }
  };

  const handleRegenerateLastAssistantMessage = async () => {
    if (isSending || !activeSessionId) return;
    setIsSending(true);

    setMessages((prev) => {
      const copy = [...prev];
      const lastAsstIdx = copy.map((m) => m.role).lastIndexOf('assistant');
      if (lastAsstIdx !== -1) {
        copy.splice(lastAsstIdx, 1);
      }
      return copy;
    });

    try {
      const res = await api.post(`/chat/sessions/${activeSessionId}/regenerate`);
      const data = res.data;
      const assistantMsg = {
        id: `resp-${Date.now()}`,
        session_id: activeSessionId,
        role: 'assistant',
        content: data.answer,
        citations: data.citations || [],
        is_fallback: data.is_fallback || false,
        low_context: data.low_context || false,
        source: data.source || (data.citations?.length ? 'rag' : 'llm_api'),
        created_at: new Date().toISOString(),
        animateReveal: true,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      console.error('Error regenerating response:', err);
      const errMsg = {
        id: `err-${Date.now()}`,
        session_id: activeSessionId,
        role: 'assistant',
        content: err.response?.data?.detail || 'Failed to regenerate response. Please try again.',
        is_error: true,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setIsSending(false);
    }
  };

  const handleExportAllConversations = async () => {
    if (sessions.length === 0) {
      alert('No conversations to export.');
      return;
    }
    try {
      const allExportData = [];
      for (const sess of sessions) {
        try {
          const msgRes = await api.get(`/chat/sessions/${sess.id}/messages`);
          allExportData.push({
            id: sess.id,
            title: sess.title,
            pinned: sess.pinned,
            created_at: sess.created_at,
            messages: msgRes.data || [],
          });
        } catch (e) {
          console.warn(`Skipped exporting messages for session ${sess.id}:`, e);
        }
      }

      const jsonBlob = new Blob([JSON.stringify(allExportData, null, 2)], {
        type: 'application/json',
      });
      const url = window.URL.createObjectURL(jsonBlob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `omnirag_all_conversations_${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Error exporting all conversations:', err);
      alert('Failed to export all conversations. Please try again.');
    }
  };

  const handleConfirmClearAllChats = async () => {
    const trimmed = clearChatsInput.trim().toUpperCase();
    if (trimmed !== 'CLEAR' && trimmed !== 'DELETE') {
      return;
    }
    setIsClearingChats(true);
    try {
      for (const sess of sessions) {
        try {
          await api.delete(`/chat/sessions/${sess.id}`);
        } catch (e) {
          console.warn(`Error deleting session ${sess.id}:`, e);
        }
      }
      setSessions([]);
      setActiveSessionId(null);
      setMessages([]);
      setClearChatsModalOpen(false);
      setClearChatsInput('');
    } catch (err) {
      console.error('Error clearing all chats:', err);
      alert('Failed to delete some chats.');
    } finally {
      setIsClearingChats(false);
    }
  };

  const handleConfirmDeleteAccount = async () => {
    if (deleteAccountInput.trim() !== 'DELETE') {
      setDeleteAccountError("Please type 'DELETE' to confirm account deletion.");
      return;
    }
    setIsDeletingAccount(true);
    setDeleteAccountError('');
    try {
      await api.delete('/auth/account');
      sessionStorage.setItem('account_deleted_notice', 'Your account and data have been permanently deleted.');
      setDeleteAccountModalOpen(false);
      setSettingsOpen(false);
      if (signOut) await signOut();
      logout();
      navigate('/');
    } catch (err) {
      console.error('Error deleting account:', err);
      setDeleteAccountError(
        err.response?.data?.detail || err.response?.data?.message || 'Failed to delete account. Please try again.'
      );
    } finally {
      setIsDeletingAccount(false);
    }
  };

  const handleFileSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const eventId = `file-${Date.now()}`;
    const ext = file.name.split('.').pop().toLowerCase();

    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }

    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setInlineEvents((prev) => [
        ...prev,
        {
          id: eventId,
          status: 'error',
          text: `Upload failed: Unsupported file type ".${ext}". Allowed formats: PDF, DOCX, TXT, CSV.`,
        },
      ]);
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      setInlineEvents((prev) => [
        ...prev,
        {
          id: eventId,
          status: 'error',
          text: `Upload failed: "${file.name}" exceeds the 50MB file size limit.`,
        },
      ]);
      return;
    }

    setInlineEvents((prev) => [
      ...prev,
      {
        id: eventId,
        status: 'uploading',
        text: `Uploading ${file.name}...`,
      },
    ]);

    try {
      const formData = new FormData();
      formData.append('username', user);
      formData.append('file', file);

      const res = await api.post('/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      const result = res.data;

      if (result.status === 'indexed' || result.status === 'parsed') {
        const chunkMsg = result.chunk_count ? `${result.chunk_count} chunks ready` : 'indexing complete';
        setInlineEvents((prev) =>
          prev.map((ev) =>
            ev.id === eventId
              ? {
                  id: eventId,
                  status: 'success',
                  text: `${result.filename} indexed — ${chunkMsg}`,
                }
              : ev
          )
        );
        fetchUserDocuments();
      } else {
        setInlineEvents((prev) =>
          prev.map((ev) =>
            ev.id === eventId
              ? {
                  id: eventId,
                  status: 'error',
                  text: `Indexing failed for ${result.filename}: ${result.error_message || 'Unsupported document structure'}`,
                }
              : ev
          )
        );
      }
    } catch (err) {
      const errorDetail = err.response?.data?.detail || err.response?.data?.message || err.message;
      setInlineEvents((prev) =>
        prev.map((ev) =>
          ev.id === eventId
            ? {
                id: eventId,
                status: 'error',
                text: `Upload failed for ${file.name}: ${errorDetail}`,
              }
            : ev
        )
      );
    }
  };

  const toggleDocSelection = (docId) => {
    setSelectedDocIds((prev) => {
      if (prev.includes(docId)) {
        return prev.filter((id) => id !== docId);
      } else {
        return [...prev, docId];
      }
    });
  };

  const handleSelectAllDocs = () => {
    if (selectedDocIds.length === 0 && documents.length > 0) {
      setSelectedDocIds(documents.map((d) => d.id));
    } else {
      setSelectedDocIds([]);
    }
  };

  const activeSessionObj = sessions.find((s) => s.id === activeSessionId);

  return (
    <div className="flex h-screen chat-surface text-slate-300 font-sans overflow-hidden">
      {/* 1. LEFT SIDEBAR */}
      <ChatSidebar
        sidebarOpen={sidebarOpen}
        setSidebarOpen={setSidebarOpen}
        sidebarCollapsed={sidebarCollapsed}
        setSidebarCollapsed={setSidebarCollapsed}
        shouldReduceMotion={shouldReduceMotion}
        sessions={sessions}
        filteredSessions={filteredSessions}
        loadingSessions={loadingSessions}
        activeSessionId={activeSessionId}
        sessionSearch={sessionSearch}
        setSessionSearch={setSessionSearch}
        collapsedSearchOpen={collapsedSearchOpen}
        setCollapsedSearchOpen={setCollapsedSearchOpen}
        handleCreateNewSession={handleCreateNewSession}
        handleSelectSession={handleSelectSession}
        handleTogglePinSession={handleTogglePinSession}
        handleStartRenameSession={handleStartRenameSession}
        editingSessionId={editingSessionId}
        editingTitle={editingTitle}
        setEditingTitle={setEditingTitle}
        setEditingSessionId={setEditingSessionId}
        handleSaveSessionTitle={handleSaveSessionTitle}
        handleDuplicateSession={handleDuplicateSession}
        handleExportSession={handleExportSession}
        handleInitiateDeleteSession={handleInitiateDeleteSession}
        activeContextMenu={activeContextMenu}
        setActiveContextMenu={setActiveContextMenu}
        user={user}
        loginMethod={loginMethod}
        setSettingsOpen={setSettingsOpen}
        handleLogout={handleLogout}
        navigate={navigate}
      />

      {/* 2. CENTER & BOTTOM: Active Chat Window & Input (Direct on page background) */}
      <main className="flex-1 flex flex-col h-full bg-transparent min-w-0 relative overflow-hidden">
        <div className="flex-1 flex flex-col min-w-0 h-full bg-transparent overflow-hidden relative">
          <ChatChatMessageList
            setSidebarOpen={setSidebarOpen}
            activeSessionObj={activeSessionObj}
            activeSessionId={activeSessionId}
            sessions={sessions}
            documents={documents}
            setDocSelectorOpen={setDocSelectorOpen}
            handleExportSession={handleExportSession}
            loadingMessages={loadingMessages}
            messages={messages}
            inlineEvents={inlineEvents}
            shouldReduceMotion={shouldReduceMotion}
            setInputQuery={setInputQuery}
            editingMessageId={editingMessageId}
            setEditingMessageId={setEditingMessageId}
            editingMessageContent={editingMessageContent}
            setEditingMessageContent={setEditingMessageContent}
            handleEditUserMessage={handleEditUserMessage}
            scrollToBottom={scrollToBottom}
            handleRevealComplete={handleRevealComplete}
            activeCitation={activeCitation}
            setActiveCitation={setActiveCitation}
            isSending={isSending}
            handleRegenerateLastAssistantMessage={handleRegenerateLastAssistantMessage}
            messagesEndRef={messagesEndRef}
          />

          <ChatInputBar
            docSelectorRef={docSelectorRef}
            shouldReduceMotion={shouldReduceMotion}
            docSelectorOpen={docSelectorOpen}
            setDocSelectorOpen={setDocSelectorOpen}
            setShowUploadMenu={setShowUploadMenu}
            selectedDocIds={selectedDocIds}
            documents={documents}
            handleSelectAllDocs={handleSelectAllDocs}
            docSearchQuery={docSearchQuery}
            setDocSearchQuery={setDocSearchQuery}
            filteredScopeDocuments={filteredScopeDocuments}
            toggleDocSelection={toggleDocSelection}
            handleSendMessage={handleSendMessage}
            fileInputRef={fileInputRef}
            handleFileSelect={handleFileSelect}
            inputQuery={inputQuery}
            setInputQuery={setInputQuery}
            isSending={isSending}
            uploadMenuRef={uploadMenuRef}
            showUploadMenu={showUploadMenu}
            uploadMenuItems={uploadMenuItems}
            ragEnabled={ragEnabled}
            setRagEnabled={setRagEnabled}
            webSearchEnabled={webSearchEnabled}
            setWebSearchEnabled={setWebSearchEnabled}
            isRecording={isRecording}
            cancelVoiceRecording={cancelVoiceRecording}
            isTranscribing={isTranscribing}
            toggleVoiceRecording={toggleVoiceRecording}
            analyserRef={analyserRef}
            audioLevels={audioLevels}
            isUndoDeleting={isUndoDeleting}
            undoSessionData={undoSessionData}
            handleUndoDelete={handleUndoDelete}
          />
        </div>
      </main>

      {/* 3. SETTINGS & ACCOUNT MODALS */}
      <ChatSettingsModal
        settingsOpen={settingsOpen}
        setSettingsOpen={setSettingsOpen}
        shouldReduceMotion={shouldReduceMotion}
        settingsTab={settingsTab}
        setSettingsTab={setSettingsTab}
        manualReduceMotion={manualReduceMotion}
        toggleManualReduceMotion={toggleManualReduceMotion}
        osReducedMotion={osReducedMotion}
        defaultRagEnabled={defaultRagEnabled}
        updateDefaultRag={updateDefaultRag}
        defaultWebSearchEnabled={defaultWebSearchEnabled}
        updateDefaultWeb={updateDefaultWeb}
        handleExportAllConversations={handleExportAllConversations}
        setClearChatsInput={setClearChatsInput}
        setClearChatsModalOpen={setClearChatsModalOpen}
        user={user}
        clerkUser={clerkUser}
        loginMethod={loginMethod}
        navigate={navigate}
        setDeleteAccountInput={setDeleteAccountInput}
        setDeleteAccountError={setDeleteAccountError}
        setDeleteAccountModalOpen={setDeleteAccountModalOpen}
        deleteAccountModalOpen={deleteAccountModalOpen}
        isDeletingAccount={isDeletingAccount}
        deleteAccountInput={deleteAccountInput}
        deleteAccountError={deleteAccountError}
        handleConfirmDeleteAccount={handleConfirmDeleteAccount}
        clearChatsModalOpen={clearChatsModalOpen}
        isClearingChats={isClearingChats}
        clearChatsInput={clearChatsInput}
        sessions={sessions}
        handleConfirmClearAllChats={handleConfirmClearAllChats}
      />
    </div>
  );
};

export default ChatLayout;
