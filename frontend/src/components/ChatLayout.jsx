import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { useNavigate } from 'react-router-dom';
import {
  Plus,
  MessageSquare,
  Trash2,
  Send,
  Bot,
  User,
  LogOut,
  Camera,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  Loader2,
  FileText,
  ChevronDown,
  Menu,
  X,
  Sparkles,
  Layers,
  SearchX,
  ScanFace,
  ShieldCheck,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

/**
 * Formats ISO timestamp to human-friendly relative time.
 */
function formatRelativeTime(dateString) {
  if (!dateString) return '';
  const date = new Date(dateString);
  const now = new Date();
  const diffInSeconds = Math.floor((now - date) / 1000);

  if (diffInSeconds < 60) return 'Just now';
  const diffInMinutes = Math.floor(diffInSeconds / 60);
  if (diffInMinutes < 60) return `${diffInMinutes}m ago`;
  const diffInHours = Math.floor(diffInMinutes / 60);
  if (diffInHours < 24) return `${diffInHours}h ago`;
  const diffInDays = Math.floor(diffInHours / 24);
  if (diffInDays < 7) return `${diffInDays}d ago`;
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export const ChatLayout = () => {
  const { user, loginMethod, logout } = useAuth();
  const navigate = useNavigate();

  // Sidebar mobile drawer state
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // User menu dropdown in top right
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  // Personalized welcome banner at top of chat area (auto-dismisses or manually dismissible)
  const [showWelcomeBanner, setShowWelcomeBanner] = useState(true);

  // Sessions state
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [loadingSessions, setLoadingSessions] = useState(true);

  // Messages state for active session
  const [messages, setMessages] = useState([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [isSending, setIsSending] = useState(false);

  // User input text
  const [inputQuery, setInputQuery] = useState('');

  // Documents state for document scope selector
  const [documents, setDocuments] = useState([]);
  const [selectedDocIds, setSelectedDocIds] = useState([]); // empty array = all documents
  const [docSelectorOpen, setDocSelectorOpen] = useState(false);

  // Inline system notifications (e.g. uploads in progress/completed)
  const [inlineEvents, setInlineEvents] = useState([]);

  // References
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const docSelectorRef = useRef(null);
  const userMenuRef = useRef(null);

  const ALLOWED_EXTENSIONS = ['pdf', 'docx', 'txt', 'csv'];
  const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB

  // Auto-scroll chat to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, inlineEvents, isSending]);

  // Click outside listener for dropdowns (Document selector and User menu)
  useEffect(() => {
    function handleClickOutside(e) {
      if (docSelectorRef.current && !docSelectorRef.current.contains(e.target)) {
        setDocSelectorOpen(false);
      }
      if (userMenuRef.current && !userMenuRef.current.contains(e.target)) {
        setUserMenuOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Auto-dismiss welcome banner after 8 seconds so it doesn't persistently occupy space
  useEffect(() => {
    const timer = setTimeout(() => {
      setShowWelcomeBanner(false);
    }, 8000);
    return () => clearTimeout(timer);
  }, [user]);

  // Fetch indexed documents for the active user in the background
  const fetchUserDocuments = async () => {
    if (!user) return;
    try {
      const res = await api.get(`/documents/${encodeURIComponent(user)}`);
      setDocuments(res.data || []);
    } catch (err) {
      console.error('Error fetching user documents:', err);
    }
  };

  // ===========================================================================
  // 1. Initial Load: Fetch sessions and documents automatically on mount/login
  // ===========================================================================
  useEffect(() => {
    let isCurrent = true;

    // Reset all session and document state when user changes to prevent flashing old data
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

    // Fetch user documents in the background immediately on login/mount
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

    // Fetch user sessions and auto-load most recent session if one exists
    const initSessions = async () => {
      setLoadingSessions(true);
      try {
        const res = await api.get(`/chat/sessions/${encodeURIComponent(user)}`);
        if (!isCurrent) return;
        const sessionList = res.data || [];
        setSessions(sessionList);

        if (sessionList.length > 0) {
          // If user has at least one existing session, automatically open their most recent session
          const mostRecentId = sessionList[0].id || sessionList[0].session_id;
          setActiveSessionId(mostRecentId);
          loadSessionMessages(mostRecentId);
        } else {
          // If no sessions yet, keep activeSessionId null to show clean "Start your first chat" empty state
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

  // ===========================================================================
  // 2. Load messages for a given session
  // ===========================================================================
  const loadSessionMessages = async (sessionId) => {
    if (!sessionId) return;
    setLoadingMessages(true);
    setInlineEvents([]); // Reset inline upload banners for newly selected session
    try {
      const res = await api.get(`/chat/sessions/${sessionId}/messages`);
      setMessages(res.data || []);
    } catch (err) {
      console.error('Error loading session messages:', err);
    } finally {
      setLoadingMessages(false);
    }
  };

  // ===========================================================================
  // 3. Switch active session
  // ===========================================================================
  const handleSelectSession = (sessionId) => {
    if (sessionId === activeSessionId) return;
    setActiveSessionId(sessionId);
    loadSessionMessages(sessionId);
    setSidebarOpen(false); // Close mobile drawer
  };

  // ===========================================================================
  // 4. Create a new session ("+ New Chat")
  // ===========================================================================
  const handleCreateNewSession = async () => {
    try {
      const res = await api.post('/chat/sessions', { username: user });
      const newSession = res.data;
      const newSessionId = newSession.session_id || newSession.id;

      const formatted = {
        id: newSessionId,
        session_id: newSessionId,
        title: newSession.title || 'New Chat',
        created_at: newSession.created_at,
      };

      setSessions((prev) => [formatted, ...prev]);
      setActiveSessionId(newSessionId);
      setMessages([]);
      setInlineEvents([]);
      setSidebarOpen(false);
      return newSessionId;
    } catch (err) {
      console.error('Error creating new session:', err);
    }
  };

  // ===========================================================================
  // 5. Delete session with confirmation prompt
  // ===========================================================================
  const handleDeleteSession = async (e, sessionId) => {
    e.stopPropagation();
    const confirmed = window.confirm('Are you sure you want to delete this chat session? All its messages will be permanently removed.');
    if (!confirmed) return;

    try {
      await api.delete(`/chat/sessions/${sessionId}`, {
        data: { username: user },
        params: { username: user },
      });

      const remaining = sessions.filter((s) => s.id !== sessionId);
      setSessions(remaining);

      // If active session was deleted, switch to first remaining or show empty state
      if (activeSessionId === sessionId) {
        if (remaining.length > 0) {
          const nextId = remaining[0].id;
          setActiveSessionId(nextId);
          loadSessionMessages(nextId);
        } else {
          setActiveSessionId(null);
          setMessages([]);
        }
      }
    } catch (err) {
      console.error('Error deleting session:', err);
      alert('Failed to delete chat session. Please try again.');
    }
  };

  // ===========================================================================
  // 6. Clean Logout Flow: Clears in-memory states and redirects
  // ===========================================================================
  const handleLogout = () => {
    // Clear all in-memory states
    setSessions([]);
    setActiveSessionId(null);
    setMessages([]);
    setDocuments([]);
    setSelectedDocIds([]);
    setInlineEvents([]);
    setInputQuery('');
    setUserMenuOpen(false);
    setDocSelectorOpen(false);

    // Clear AuthContext & session storage
    logout();

    // Redirect to login choice
    navigate('/');
  };

  // ===========================================================================
  // 7. Send message
  // ===========================================================================
  const handleSendMessage = async (e) => {
    e?.preventDefault();
    const trimmed = inputQuery.trim();
    if (!trimmed || isSending) return;

    let targetSessionId = activeSessionId;

    // If user has no active session yet (e.g. first-time empty state), create one first
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

    // Create optimistic user message
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
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, assistantMsg]);

      // If current session title was "New Chat", auto-update title in sidebar
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

  // ===========================================================================
  // 8. Handle file upload via "+" button directly in chat input bar
  // ===========================================================================
  const handleFileSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const eventId = `file-${Date.now()}`;
    const ext = file.name.split('.').pop().toLowerCase();

    // Reset file input value so user can upload again if needed
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }

    // Validation: format
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

    // Validation: size
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

    // Add progress event: "Uploading [filename]..."
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
        // Refresh document list so new doc is immediately available in selector
        fetchUserDocuments();
      } else {
        // Document uploaded but parsing or indexing failed
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

  // Document selection helper
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
    <div className="flex h-screen w-full bg-slate-950 text-slate-100 overflow-hidden font-sans">
      {/* ========================================================================= */}
      {/* 1. LEFT SIDEBAR: Session History & Navigation                             */}
      {/* ========================================================================= */}
      {/* Mobile backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-40 md:hidden backdrop-blur-xs transition-opacity"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <aside
        className={`
          fixed md:relative z-50 md:z-0 top-0 left-0 h-full w-72 lg:w-80
          bg-slate-900 border-r border-slate-800/80 flex flex-col shrink-0
          transition-transform duration-200 ease-in-out
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
        `}
      >
        {/* Sidebar Header: App Brand */}
        <div className="p-4 border-b border-slate-800/80 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-md shadow-indigo-600/30">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <h1 className="font-bold text-slate-100 text-sm tracking-tight flex items-center gap-1.5">
                OmniRAG AI
                <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  RAG
                </span>
              </h1>
              <p className="text-[11px] text-slate-400">Contextual Knowledge Chat</p>
            </div>
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            className="md:hidden p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* "+ New Chat" Button */}
        <div className="p-3 border-b border-slate-800/60">
          <button
            onClick={handleCreateNewSession}
            className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 active:scale-[0.99] text-white font-medium text-xs sm:text-sm shadow-md shadow-indigo-600/25 transition-all"
          >
            <Plus className="w-4 h-4 stroke-[2.5]" />
            <span>New Chat</span>
          </button>
        </div>

        {/* Sessions History List */}
        <div className="flex-1 overflow-y-auto px-2 py-3 space-y-1 scrollbar-thin scrollbar-thumb-slate-700">
          <div className="px-2 py-1 flex items-center justify-between text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            <span>Conversations</span>
            <span className="text-[10px] bg-slate-800 px-1.5 py-0.5 rounded text-slate-300">
              {sessions.length}
            </span>
          </div>

          {loadingSessions ? (
            <div className="p-4 text-center text-slate-400 text-xs flex items-center justify-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
              <span>Loading chats...</span>
            </div>
          ) : sessions.length === 0 ? (
            <div className="p-4 text-center text-slate-500 text-xs leading-relaxed">
              No previous conversations. Click &quot;+ New Chat&quot; or ask a question to start.
            </div>
          ) : (
            sessions.map((sess) => {
              const isActive = sess.id === activeSessionId;
              return (
                <div
                  key={sess.id}
                  onClick={() => handleSelectSession(sess.id)}
                  className={`
                    group relative flex items-center justify-between p-2.5 rounded-xl cursor-pointer text-xs transition-all
                    ${
                      isActive
                        ? 'bg-slate-800 text-white font-medium shadow-sm border border-slate-700/60'
                        : 'text-slate-300 hover:bg-slate-800/60 hover:text-white border border-transparent'
                    }
                  `}
                >
                  <div className="flex items-center gap-2.5 min-w-0 pr-2">
                    <MessageSquare
                      className={`w-4 h-4 shrink-0 ${isActive ? 'text-indigo-400' : 'text-slate-500 group-hover:text-slate-400'}`}
                    />
                    <div className="min-w-0">
                      <p className="truncate text-xs leading-tight">{sess.title || 'New Chat'}</p>
                      <p className="text-[10px] text-slate-400 mt-0.5">
                        {formatRelativeTime(sess.created_at)}
                      </p>
                    </div>
                  </div>

                  {/* Delete session icon (visible on hover) */}
                  <button
                    onClick={(e) => handleDeleteSession(e, sess.id)}
                    title="Delete chat session"
                    className="opacity-0 group-hover:opacity-100 p-1.5 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-all shrink-0"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })
          )}
        </div>

        {/* Sidebar Footer: User Status summary */}
        <div className="p-3 border-t border-slate-800/80 bg-slate-900/90 space-y-2">
          <div className="flex items-center justify-between text-xs px-1">
            <div className="flex items-center gap-2 min-w-0">
              <div className="w-7 h-7 rounded-full bg-gradient-to-tr from-indigo-600 to-indigo-500 flex items-center justify-center text-white font-semibold text-xs shrink-0 shadow-xs">
                {user ? user.charAt(0).toUpperCase() : 'U'}
              </div>
              <div className="min-w-0">
                <p className="truncate font-medium text-slate-200 leading-none">{user}</p>
                <p className="text-[10px] text-slate-400 mt-0.5 flex items-center gap-1">
                  {loginMethod === 'face' ? (
                    <span className="text-emerald-400 flex items-center gap-0.5">
                      <ScanFace className="w-3 h-3" /> Face Verified
                    </span>
                  ) : (
                    <span>Password Auth</span>
                  )}
                </p>
              </div>
            </div>
            <button
              onClick={() => navigate('/account/add-face')}
              title="Biometric Face Login Settings"
              className="p-1.5 rounded-lg text-slate-400 hover:text-indigo-300 hover:bg-indigo-600/20 border border-transparent hover:border-indigo-500/30 transition-all"
            >
              <Camera className="w-4 h-4" />
            </button>
          </div>

          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-lg text-xs text-slate-400 hover:text-rose-300 hover:bg-rose-500/10 border border-slate-800 hover:border-rose-500/30 transition-all"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* ========================================================================= */}
      {/* 2. CENTER & BOTTOM: Active Chat Window & Input                            */}
      {/* ========================================================================= */}
      <main className="flex-1 flex flex-col h-full bg-slate-950 min-w-0 relative">
        {/* Top Header Bar */}
        <header className="h-14 border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-md px-4 flex items-center justify-between shrink-0 z-20">
          <div className="flex items-center gap-3 min-w-0">
            <button
              onClick={() => setSidebarOpen(true)}
              className="md:hidden p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div className="min-w-0">
              <h2 className="font-semibold text-sm text-slate-200 truncate">
                {activeSessionObj?.title || (sessions.length > 0 ? 'OmniRAG Chat' : 'New Conversation')}
              </h2>
              <p className="text-[11px] text-slate-400 truncate flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block"></span>
                <span>{documents.length} document{documents.length === 1 ? '' : 's'} in knowledge base</span>
              </p>
            </div>
          </div>

          {/* User Menu in Top-Right Corner (Task 4) */}
          <div className="relative" ref={userMenuRef}>
            <button
              type="button"
              onClick={() => setUserMenuOpen((prev) => !prev)}
              className="flex items-center gap-2 px-2.5 py-1.5 rounded-xl bg-slate-800/80 hover:bg-slate-800 border border-slate-700/80 text-xs font-medium text-slate-200 transition-all cursor-pointer shadow-xs focus:outline-none"
            >
              {/* Avatar Initial Circle */}
              <div className="relative w-7 h-7 rounded-full bg-gradient-to-tr from-indigo-600 to-indigo-500 flex items-center justify-center text-white font-bold text-xs shadow-xs">
                {user ? user.charAt(0).toUpperCase() : 'U'}
                {loginMethod === 'face' && (
                  <span
                    title="Logged in via Face Recognition"
                    className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-emerald-400 ring-2 ring-slate-900"
                  />
                )}
              </div>
              <span className="hidden sm:inline truncate max-w-[120px]">{user}</span>
              <ChevronDown
                className={`w-3.5 h-3.5 text-slate-400 transition-transform duration-200 ${
                  userMenuOpen ? 'rotate-180' : ''
                }`}
              />
            </button>

            {/* Dropdown Menu */}
            {userMenuOpen && (
              <div className="absolute right-0 mt-2 w-56 bg-slate-900 border border-slate-700/90 rounded-2xl shadow-2xl py-1.5 z-50 text-xs">
                {/* User info summary */}
                <div className="px-3.5 py-2.5 border-b border-slate-800/80">
                  <p className="font-semibold text-slate-100 truncate">{user}</p>
                  <p className="text-[11px] text-slate-400 flex items-center gap-1 mt-0.5">
                    {loginMethod === 'face' ? (
                      <>
                        <ScanFace className="w-3.5 h-3.5 text-emerald-400" />
                        <span className="text-emerald-400 font-medium">Face ID Verified</span>
                      </>
                    ) : (
                      <>
                        <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
                        <span>Password Verified</span>
                      </>
                    )}
                  </p>
                </div>

                {/* Dropdown items */}
                <div className="py-1">
                  <button
                    onClick={() => {
                      setUserMenuOpen(false);
                      navigate('/account/add-face');
                    }}
                    className="w-full flex items-center gap-2.5 px-3.5 py-2 text-slate-300 hover:text-white hover:bg-slate-800/80 transition-colors text-left"
                  >
                    <Camera className="w-4 h-4 text-indigo-400 shrink-0" />
                    <span>Add / Update Face</span>
                  </button>

                  <div className="border-t border-slate-800/60 my-1"></div>

                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center gap-2.5 px-3.5 py-2 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors text-left"
                  >
                    <LogOut className="w-4 h-4 shrink-0" />
                    <span>Log Out</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </header>

        {/* Personalized Welcome Element at Top of Chat Area (Task 3) */}
        {showWelcomeBanner && (
          <div className="mx-4 mt-3 mb-1 sm:mx-6 p-3 rounded-xl bg-slate-900/95 border border-indigo-500/25 shadow-md flex items-center justify-between gap-3 text-xs shrink-0 transition-all">
            <div className="flex items-center gap-2.5 flex-wrap">
              <div className="w-6 h-6 rounded-lg bg-indigo-600/20 text-indigo-400 flex items-center justify-center shrink-0">
                <Sparkles className="w-3.5 h-3.5" />
              </div>
              <span className="font-semibold text-slate-100 text-xs sm:text-sm">
                {sessions.length > 0
                  ? `Welcome back, ${user}`
                  : `Welcome, ${user} — let's get started`}
              </span>

              {/* Biometric acknowledgement badge if signed in via face */}
              {loginMethod === 'face' && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 shadow-xs">
                  <ScanFace className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Face Recognition Verified</span>
                </span>
              )}
              {loginMethod === 'password' && (
                <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium bg-slate-800 text-slate-400 border border-slate-700">
                  <ShieldCheck className="w-3 h-3 text-indigo-400" />
                  <span>Password Verified</span>
                </span>
              )}
            </div>

            <button
              onClick={() => setShowWelcomeBanner(false)}
              title="Dismiss banner"
              className="p-1 rounded-md text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-all shrink-0"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Scrollable Chat Message History */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 scrollbar-thin scrollbar-thumb-slate-800">
          {loadingMessages ? (
            <div className="h-full flex items-center justify-center text-slate-500 text-xs gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-indigo-500" />
              <span>Loading messages...</span>
            </div>
          ) : activeSessionId === null || sessions.length === 0 ? (
            /* Clean "Start your first chat" Empty State (Task 2) */
            <div className="h-full flex flex-col items-center justify-center text-center max-w-md mx-auto p-6 space-y-4">
              <div className="w-14 h-14 rounded-2xl bg-indigo-600/15 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shadow-inner">
                <Sparkles className="w-7 h-7" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">Start your first chat</h3>
                <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                  Welcome, <strong className="text-slate-200">{user}</strong>! You don&apos;t have any active conversations yet. Ask a question below or upload documents to start your personal knowledge base.
                </p>
              </div>

              <button
                onClick={handleCreateNewSession}
                className="inline-flex items-center gap-2 py-2 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 active:scale-[0.99] text-white font-medium text-xs shadow-md shadow-indigo-600/25 transition-all"
              >
                <Plus className="w-4 h-4 stroke-[2.5]" />
                <span>Create New Chat</span>
              </button>

              {documents.length > 0 && (
                <div className="w-full bg-slate-900/80 border border-slate-800 rounded-xl p-3 text-left mt-2">
                  <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
                    Your Indexed Documents ({documents.length}):
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {documents.slice(0, 4).map((doc) => (
                      <span
                        key={doc.id}
                        className="inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded-md bg-slate-800 border border-slate-700 text-slate-300"
                      >
                        <FileText className="w-3 h-3 text-indigo-400" />
                        <span className="truncate max-w-[140px]">{doc.original_filename}</span>
                      </span>
                    ))}
                    {documents.length > 4 && (
                      <span className="text-[11px] text-slate-500 self-center">
                        +{documents.length - 4} more
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>
          ) : messages.length === 0 && inlineEvents.length === 0 ? (
            /* Active session is empty (waiting for first message) */
            <div className="h-full flex flex-col items-center justify-center text-center max-w-md mx-auto p-6 space-y-4">
              <div className="w-14 h-14 rounded-2xl bg-indigo-600/15 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shadow-inner">
                <Bot className="w-7 h-7" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">OmniRAG AI Knowledge Assistant</h3>
                <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                  Ask questions grounded in your uploaded documents. Use the <strong className="text-slate-300">+</strong> button in the input bar to upload new documents directly into your chat knowledge base.
                </p>
              </div>

              {documents.length > 0 ? (
                <div className="w-full bg-slate-900/80 border border-slate-800 rounded-xl p-3 text-left">
                  <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
                    Available Documents ({documents.length}):
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {documents.slice(0, 4).map((doc) => (
                      <span
                        key={doc.id}
                        className="inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded-md bg-slate-800 border border-slate-700 text-slate-300"
                      >
                        <FileText className="w-3 h-3 text-indigo-400" />
                        <span className="truncate max-w-[140px]">{doc.original_filename}</span>
                      </span>
                    ))}
                    {documents.length > 4 && (
                      <span className="text-[11px] text-slate-500 self-center">
                        +{documents.length - 4} more
                      </span>
                    )}
                  </div>
                </div>
              ) : (
                <div className="text-xs text-amber-400/90 bg-amber-500/10 border border-amber-500/20 rounded-xl p-3 flex items-center gap-2 text-left">
                  <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400" />
                  <span>No documents indexed yet. Click the <strong>+</strong> button below to upload a PDF, DOCX, TXT, or CSV file.</span>
                </div>
              )}
            </div>
          ) : (
            /* Render Message History */
            <>
              {messages.map((msg) => {
                const isUser = msg.role === 'user';
                const isError = msg.is_error;
                const isFallback = msg.is_fallback && !isError;

                if (isUser) {
                  return (
                    <div key={msg.id} className="flex justify-end items-end gap-2">
                      <div className="max-w-2xl bg-indigo-600 text-white rounded-2xl rounded-br-xs px-4 py-3 text-xs sm:text-sm shadow-sm leading-relaxed whitespace-pre-wrap">
                        {msg.content}
                      </div>
                      <div className="w-6 h-6 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 shrink-0 text-[10px]">
                        <User className="w-3.5 h-3.5" />
                      </div>
                    </div>
                  );
                }

                // Assistant Message
                return (
                  <div key={msg.id} className="flex justify-start items-start gap-3">
                    <div
                      className={`
                        w-7 h-7 rounded-xl flex items-center justify-center shrink-0 mt-0.5 shadow-sm
                        ${
                          isError
                            ? 'bg-rose-950/50 border border-rose-500/40 text-rose-400'
                            : isFallback
                            ? 'bg-amber-950/50 border border-amber-500/40 text-amber-400'
                            : 'bg-indigo-600/20 border border-indigo-500/40 text-indigo-400'
                        }
                      `}
                    >
                      {isError ? <AlertCircle className="w-4 h-4" /> : isFallback ? <SearchX className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                    </div>

                    <div
                      className={`
                        max-w-3xl rounded-2xl rounded-tl-xs p-4 text-xs sm:text-sm shadow-sm leading-relaxed
                        ${
                          isError
                            ? 'bg-slate-900/90 border border-rose-500/30 text-rose-200'
                            : isFallback
                            ? 'bg-slate-900/90 border border-amber-500/30 text-slate-300'
                            : 'bg-slate-900/90 border border-slate-800 text-slate-200'
                        }
                      `}
                    >
                      {/* Connection / Service Error badge */}
                      {isError && (
                        <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-rose-500/10 border border-rose-500/25 text-rose-400 mb-2">
                          <AlertCircle className="w-3 h-3" />
                          <span>Connection Error</span>
                        </div>
                      )}

                      {/* Fallback distinct badge */}
                      {isFallback && (
                        <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-500/10 border border-amber-500/25 text-amber-400 mb-2">
                          <SearchX className="w-3 h-3" />
                          <span>Information Not Found in Context</span>
                        </div>
                      )}

                      {/* User messages stay plain text; assistant answers are trusted markdown from our formatter. */}
                      <ReactMarkdown
                        components={{
                          p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
                          ul: ({ children }) => <ul className="my-3 list-disc space-y-2 pl-5">{children}</ul>,
                          ol: ({ children }) => <ol className="my-3 list-decimal space-y-2 pl-5">{children}</ol>,
                          li: ({ children }) => <li className="pl-1">{children}</li>,
                          strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
                        }}
                      >
                        {msg.content}
                      </ReactMarkdown>

                      {/* Source Citations Badges */}
                      {!isFallback && msg.citations && msg.citations.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-slate-800/80 space-y-1.5">
                          <p className="text-[10px] uppercase font-bold tracking-wider text-indigo-400 flex items-center gap-1">
                            <span>Sources &amp; Citations</span>
                          </p>
                          <div className="flex flex-wrap gap-1.5">
                            {msg.citations.map((c, i) => {
                              const chunks = c.chunk_references || [];
                              const chunkStr = chunks.length > 0 ? ` (chunk${chunks.length > 1 ? 's' : ''} ${chunks.join(', ')})` : '';
                              return (
                                <span
                                  key={i}
                                  className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px] bg-slate-800 border border-indigo-500/30 text-indigo-300 font-medium"
                                >
                                  <FileText className="w-3 h-3 text-indigo-400 shrink-0" />
                                  <span className="truncate max-w-[180px]">{c.filename}</span>
                                  <span className="text-[10px] text-indigo-400/80">{chunkStr}</span>
                                </span>
                              );
                            })}
                          </div>
                        </div>
                      )}

                      {/* Low-Context Indicator Badge */}
                      {!isFallback && msg.low_context && (
                        <div className="mt-2.5">
                          <span className="inline-flex items-center gap-1 text-[11px] font-medium text-amber-400/90 bg-amber-500/10 border border-amber-500/25 px-2 py-0.5 rounded-full">
                            <AlertTriangle className="w-3 h-3 text-amber-400" />
                            <span>Limited context: Answer synthesized from fewer source chunks.</span>
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}

              {/* Inline System Notifications for uploads */}
              {inlineEvents.map((ev) => (
                <div key={ev.id} className="flex justify-center my-2">
                  <div
                    className={`
                      inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-medium shadow-sm transition-all
                      ${
                        ev.status === 'uploading'
                          ? 'bg-slate-800/95 border border-indigo-500/40 text-indigo-300'
                          : ev.status === 'success'
                          ? 'bg-emerald-950/60 border border-emerald-500/40 text-emerald-300'
                          : 'bg-rose-950/60 border border-rose-500/40 text-rose-300'
                      }
                    `}
                  >
                    {ev.status === 'uploading' && <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-400" />}
                    {ev.status === 'success' && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />}
                    {ev.status === 'error' && <AlertCircle className="w-3.5 h-3.5 text-rose-400" />}
                    <span>{ev.text}</span>
                  </div>
                </div>
              ))}

              {/* Sending / Thinking loading state */}
              {isSending && (
                <div className="flex justify-start items-start gap-3">
                  <div className="w-7 h-7 rounded-xl bg-indigo-600/20 border border-indigo-500/40 flex items-center justify-center text-indigo-400 shadow-sm shrink-0">
                    <Bot className="w-4 h-4" />
                  </div>
                  <div className="bg-slate-900/90 border border-slate-800 rounded-2xl rounded-tl-xs px-4 py-3 text-xs text-slate-400 flex items-center gap-2 shadow-sm">
                    <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-400" />
                    <span>Searching vector knowledge base &amp; formulating response...</span>
                  </div>
                </div>
              )}
            </>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* ======================================================================= */}
        {/* 3. BOTTOM: Document Selector & Input Bar                                */}
        {/* ======================================================================= */}
        <div className="p-3 sm:p-4 bg-slate-900/80 border-t border-slate-800/80 backdrop-blur-md shrink-0 space-y-2">
          {/* Document Scope Selector Button & Popover */}
          <div className="relative inline-block" ref={docSelectorRef}>
            <button
              type="button"
              onClick={() => setDocSelectorOpen((prev) => !prev)}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium bg-slate-800/90 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-700/80 transition-all shadow-xs"
            >
              <Layers className="w-3.5 h-3.5 text-indigo-400" />
              <span>
                {selectedDocIds.length === 0
                  ? `All Documents (${documents.length})`
                  : `${selectedDocIds.length} of ${documents.length} docs selected`}
              </span>
              <ChevronDown className={`w-3 h-3 text-slate-400 transition-transform ${docSelectorOpen ? 'rotate-180' : ''}`} />
            </button>

            {/* Document Selector Dropdown Menu */}
            {docSelectorOpen && (
              <div className="absolute bottom-full mb-2 left-0 z-30 w-72 sm:w-80 bg-slate-900 border border-slate-700/90 rounded-xl shadow-2xl p-2.5 max-h-64 overflow-y-auto scrollbar-thin scrollbar-thumb-slate-700">
                <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-800">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                    Query Retrieval Scope
                  </span>
                  <button
                    onClick={handleSelectAllDocs}
                    className="text-[11px] text-indigo-400 hover:text-indigo-300 font-medium"
                  >
                    {selectedDocIds.length === 0 ? 'Select Specific' : 'Query All'}
                  </button>
                </div>

                {documents.length === 0 ? (
                  <div className="p-2 text-center text-xs text-slate-500">
                    No indexed documents found. Upload a file using the + button.
                  </div>
                ) : (
                  <div className="space-y-1">
                    {/* All Documents Option */}
                    <label className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-slate-800 cursor-pointer text-xs text-slate-200">
                      <input
                        type="checkbox"
                        checked={selectedDocIds.length === 0}
                        onChange={handleSelectAllDocs}
                        className="rounded border-slate-700 text-indigo-600 focus:ring-0 focus:ring-offset-0 bg-slate-800"
                      />
                      <span className="font-semibold text-slate-100">All Documents</span>
                      <span className="ml-auto text-[10px] text-slate-500">({documents.length})</span>
                    </label>

                    <div className="border-t border-slate-800/60 my-1"></div>

                    {/* Individual Documents */}
                    {documents.map((doc) => {
                      const isSelected = selectedDocIds.includes(doc.id);
                      return (
                        <label
                          key={doc.id}
                          className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-slate-800 cursor-pointer text-xs text-slate-300"
                        >
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => toggleDocSelection(doc.id)}
                            className="rounded border-slate-700 text-indigo-600 focus:ring-0 focus:ring-offset-0 bg-slate-800"
                          />
                          <FileText className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                          <span className="truncate flex-1" title={doc.original_filename}>
                            {doc.original_filename}
                          </span>
                          <span className="text-[10px] text-slate-500 shrink-0">
                            {doc.chunk_count ? `${doc.chunk_count} ch` : doc.file_type}
                          </span>
                        </label>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Chat Input Bar */}
          <form onSubmit={handleSendMessage} className="flex items-center gap-2">
            {/* Hidden File Picker restricted to .pdf,.docx,.txt,.csv */}
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileSelect}
              accept=".pdf,.docx,.txt,.csv"
              className="hidden"
            />

            <div className="flex-1 flex items-center gap-2 bg-slate-900/80 border border-slate-700/80 rounded-2xl px-2 py-1.5 focus-within:border-indigo-500 focus-within:ring-1 focus-within:ring-indigo-500/20 transition-all">
              {/* "+" Upload Button */}
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                title="Upload document (.pdf, .docx, .txt, .csv, max 50MB)"
                className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-700/60 transition-all shrink-0 active:scale-95"
              >
                <Plus className="w-5 h-5 stroke-[2.5]" />
              </button>

              {/* Query Text Field */}
              <input
                type="text"
                value={inputQuery}
                onChange={(e) => setInputQuery(e.target.value)}
                placeholder={
                  documents.length === 0
                    ? 'Ask a question or upload a document using + ...'
                    : 'Ask a question about your uploaded documents...'
                }
                disabled={isSending}
                className="w-full bg-transparent text-xs sm:text-sm text-slate-100 placeholder-slate-500 focus:outline-none py-1.5"
              />

              {/* Send Button */}
              <button
                type="submit"
                disabled={!inputQuery.trim() || isSending}
                title="Send query"
                className="p-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-600 text-white transition-all shadow-sm shrink-0 active:scale-95"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </form>
        </div>
      </main>
    </div>
  );
};

export default ChatLayout;
