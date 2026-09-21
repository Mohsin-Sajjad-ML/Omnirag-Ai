import React from 'react';
import { m, AnimatePresence } from 'motion/react';
import {
  Bot,
  Plus,
  Search,
  X,
  MessageSquare,
  Pin,
  MoreVertical,
  Pencil,
  Copy,
  FileText,
  Sparkles,
  Trash2,
  Loader2,
  SearchX,
  ChevronLeft,
  ChevronRight,
  Settings,
  Camera,
  ScanFace,
  ShieldCheck,
  LogOut,
} from 'lucide-react';

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

export const ChatSidebar = ({
  sidebarOpen,
  setSidebarOpen,
  sidebarCollapsed,
  setSidebarCollapsed,
  shouldReduceMotion,
  sessions,
  filteredSessions,
  loadingSessions,
  activeSessionId,
  sessionSearch,
  setSessionSearch,
  collapsedSearchOpen,
  setCollapsedSearchOpen,
  handleCreateNewSession,
  handleSelectSession,
  handleTogglePinSession,
  handleStartRenameSession,
  editingSessionId,
  editingTitle,
  setEditingTitle,
  setEditingSessionId,
  handleSaveSessionTitle,
  handleDuplicateSession,
  handleExportSession,
  handleInitiateDeleteSession,
  activeContextMenu,
  setActiveContextMenu,
  user,
  loginMethod,
  setSettingsOpen,
  handleLogout,
  navigate,
}) => {
  const renderSessionItem = (sess) => {
    const isActive = sess.id === activeSessionId;
    const isEditing = editingSessionId === sess.id;

    return (
      <m.div
        key={sess.id}
        whileHover={shouldReduceMotion ? {} : { scale: 1.02 }}
        whileTap={shouldReduceMotion || isEditing ? {} : { scale: 0.97 }}
        transition={{ duration: 0.15 }}
        onClick={() => {
          if (!isEditing) handleSelectSession(sess.id);
        }}
        style={{ zIndex: activeContextMenu === sess.id ? 50 : undefined }}
        className={`
          group session-item w-full flex items-center justify-between p-2.5 rounded-xl cursor-pointer text-left relative transition-colors
          ${activeContextMenu === sess.id ? 'z-50' : isActive ? 'z-10' : 'z-0'}
          ${
            isActive
              ? 'text-white font-medium'
              : 'text-slate-300 hover:text-white'
          }
        `}
      >
        {isActive && (
          <m.div
            layoutId={shouldReduceMotion ? undefined : 'active-session-highlight'}
            className="absolute inset-0 glass-panel bg-white/10 rounded-xl border border-white/20 shadow-sm pointer-events-none z-0"
            transition={
              shouldReduceMotion
                ? { duration: 0 }
                : { type: 'spring', stiffness: 380, damping: 30 }
            }
          />
        )}
        <div className="flex items-center gap-2.5 min-w-0 pr-1 relative z-10 flex-1">
          <MessageSquare
            className={`w-4 h-4 shrink-0 ${isActive ? 'text-violet-400' : 'text-slate-500 group-hover:text-slate-400'}`}
          />
          <div className="min-w-0 flex-1">
            {isEditing ? (
              <input
                autoFocus
                type="text"
                value={editingTitle}
                maxLength={60}
                onClick={(e) => e.stopPropagation()}
                onChange={(e) => setEditingTitle(e.target.value.slice(0, 60))}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleSaveSessionTitle(sess.id, sess.title);
                  } else if (e.key === 'Escape') {
                    e.preventDefault();
                    setEditingSessionId(null);
                    setEditingTitle('');
                  }
                }}
                onBlur={() => handleSaveSessionTitle(sess.id, sess.title)}
                className="w-full bg-slate-900/90 border border-violet-500 text-white rounded-md px-1.5 py-0.5 text-xs outline-none focus:ring-1 focus:ring-violet-400"
              />
            ) : (
              <>
                <p className="truncate text-xs leading-tight">{sess.title || 'New Chat'}</p>
                <p className="text-[10px] text-slate-400 mt-0.5">
                  {formatRelativeTime(sess.created_at)}
                </p>
              </>
            )}
          </div>
        </div>

        {/* Three-dot context menu trigger and dropdown */}
        {!isEditing && (
          <div className={`relative shrink-0 flex items-center ${activeContextMenu === sess.id ? 'z-50' : 'z-20'}`}>
            {sess.pinned && (
              <Pin className="w-3 h-3 text-violet-400 fill-violet-400 shrink-0 mr-1 opacity-80" />
            )}
            <m.button
              type="button"
              whileHover={shouldReduceMotion ? {} : { scale: 1.1 }}
              whileTap={shouldReduceMotion ? {} : { scale: 0.9 }}
              transition={{ duration: 0.15 }}
              onClick={(e) => {
                e.stopPropagation();
                setActiveContextMenu(activeContextMenu === sess.id ? null : sess.id);
              }}
              title="Session options"
              className={`session-context-trigger p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-all ${
                activeContextMenu === sess.id ? 'opacity-100 text-white bg-white/15' : 'opacity-0 group-hover:opacity-100'
              }`}
            >
              <MoreVertical className="w-3.5 h-3.5" />
            </m.button>

            <AnimatePresence>
              {activeContextMenu === sess.id && (
                <m.div
                  initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.95, y: -4 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.95, y: -4 }}
                  transition={{ duration: 0.15, ease: 'easeOut' }}
                  onClick={(e) => e.stopPropagation()}
                  className="session-context-menu-container absolute right-0 top-full mt-1 z-50 w-52 rounded-xl bg-[#0f0e1a]/98 border border-violet-500/30 shadow-2xl shadow-black/90 p-1.5 text-xs backdrop-blur-2xl space-y-0.5"
                >
                  <button
                    type="button"
                    onClick={() => handleTogglePinSession(sess.id, !sess.pinned)}
                    className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-violet-600/20 transition-colors text-left cursor-pointer"
                  >
                    <Pin className={`w-3.5 h-3.5 text-violet-400 ${sess.pinned ? 'fill-violet-400' : ''}`} />
                    <span>{sess.pinned ? 'Unpin chat' : 'Pin chat'}</span>
                  </button>

                  <button
                    type="button"
                    onClick={(e) => {
                      setActiveContextMenu(null);
                      handleStartRenameSession(e, sess);
                    }}
                    className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-violet-600/20 transition-colors text-left cursor-pointer"
                  >
                    <Pencil className="w-3.5 h-3.5 text-indigo-400" />
                    <span>Rename</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleDuplicateSession(sess.id)}
                    className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-violet-600/20 transition-colors text-left cursor-pointer"
                  >
                    <Copy className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Duplicate</span>
                  </button>

                  <div className="my-1 border-t border-white/10" />

                  {/* Export Option 1: Full Chat Material */}
                  <div className="flex items-center justify-between px-2 py-1.5 rounded-lg text-slate-300 hover:bg-white/[0.04] transition-colors">
                    <div className="flex items-center gap-2">
                      <FileText className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                      <span className="font-medium text-slate-200">Full Chat</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => handleExportSession(sess.id, 'txt', 'full', sess.title)}
                        title="Export full transcript as TXT"
                        className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-white/10 hover:bg-amber-500/25 text-slate-300 hover:text-amber-200 transition-colors cursor-pointer"
                      >
                        TXT
                      </button>
                      <button
                        type="button"
                        onClick={() => handleExportSession(sess.id, 'pdf', 'full', sess.title)}
                        title="Export full transcript as PDF"
                        className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-white/10 hover:bg-pink-500/25 text-slate-300 hover:text-pink-200 transition-colors cursor-pointer"
                      >
                        PDF
                      </button>
                    </div>
                  </div>

                  {/* Export Option 2: Compressed Context */}
                  <div className="flex items-center justify-between px-2 py-1.5 rounded-lg text-slate-300 hover:bg-white/[0.04] transition-colors">
                    <div className="flex items-center gap-2" title="Compressed context to continue in next chat">
                      <Sparkles className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                      <span className="font-medium text-slate-200">Chat Context</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => handleExportSession(sess.id, 'txt', 'context', sess.title)}
                        title="Export compressed context as TXT to continue conversation"
                        className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-white/10 hover:bg-cyan-500/25 text-slate-300 hover:text-cyan-200 transition-colors cursor-pointer"
                      >
                        TXT
                      </button>
                      <button
                        type="button"
                        onClick={() => handleExportSession(sess.id, 'pdf', 'context', sess.title)}
                        title="Export compressed context as PDF to continue conversation"
                        className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-white/10 hover:bg-indigo-500/25 text-slate-300 hover:text-indigo-200 transition-colors cursor-pointer"
                      >
                        PDF
                      </button>
                    </div>
                  </div>

                  <div className="my-1 border-t border-white/10" />

                  <button
                    type="button"
                    onClick={() => handleInitiateDeleteSession(sess)}
                    className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-rose-400 hover:text-rose-200 hover:bg-rose-500/20 transition-colors text-left cursor-pointer"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>Delete chat</span>
                  </button>
                </m.div>
              )}
            </AnimatePresence>
          </div>
        )}
      </m.div>
    );
  };

  return (
    <>
      {/* Mobile backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-40 md:hidden backdrop-blur-xs transition-opacity"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <aside
        className={`
          fixed md:relative z-30 top-0 left-0 h-full
          ${sidebarCollapsed ? 'w-16 overflow-visible' : 'w-72 lg:w-80 overflow-hidden'}
          glass-panel border-r border-white/10 flex flex-col shrink-0
          ${shouldReduceMotion ? '' : 'transition-[width] duration-300 ease-in-out'}
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
        `}
      >
        {sidebarCollapsed ? (
          /* Collapsed Icon-Only Slim Rail (~64px) */
          <div className="flex flex-col items-center justify-between h-full py-4 w-16 select-none shrink-0 overflow-visible">
            <div className="flex flex-col items-center gap-4 w-full">
              <m.button
                type="button"
                whileHover={shouldReduceMotion ? {} : { scale: 1.08 }}
                whileTap={shouldReduceMotion ? {} : { scale: 0.92 }}
                onClick={() => {
                  setSidebarCollapsed(false);
                  localStorage.setItem('omnirag_sidebar_collapsed', 'false');
                }}
                title="Expand sidebar"
                className="w-10 h-10 rounded-xl bg-gradient-to-tr from-violet-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-violet-600/30 cursor-pointer group relative"
              >
                <Bot className="w-5 h-5 group-hover:hidden" />
                <ChevronRight className="w-5 h-5 hidden group-hover:block text-white" />
              </m.button>

              <m.button
                type="button"
                whileHover={shouldReduceMotion ? {} : { scale: 1.08 }}
                whileTap={shouldReduceMotion ? {} : { scale: 0.92 }}
                onClick={handleCreateNewSession}
                title="New chat"
                className="w-9 h-9 rounded-xl bg-violet-600/20 hover:bg-violet-600 text-violet-300 hover:text-white border border-violet-500/30 flex items-center justify-center transition-colors cursor-pointer shadow-xs"
              >
                <Plus className="w-4 h-4 stroke-[2.5]" />
              </m.button>

              <div className="relative">
                <m.button
                  type="button"
                  whileHover={shouldReduceMotion ? {} : { scale: 1.08 }}
                  whileTap={shouldReduceMotion ? {} : { scale: 0.92 }}
                  onClick={() => setCollapsedSearchOpen((prev) => !prev)}
                  title="Search conversations"
                  className={`w-9 h-9 rounded-xl flex items-center justify-center transition-colors cursor-pointer border ${
                    collapsedSearchOpen
                      ? 'bg-violet-600 text-white border-violet-400 shadow-md shadow-violet-600/30'
                      : 'bg-white/[0.04] hover:bg-white/[0.1] text-slate-400 hover:text-slate-200 border-white/10'
                  }`}
                >
                  <Search className="w-4 h-4" />
                </m.button>

                <AnimatePresence>
                  {collapsedSearchOpen && (
                    <>
                      <div
                        className="fixed inset-0 z-40 bg-transparent"
                        onClick={() => setCollapsedSearchOpen(false)}
                      />
                      <m.div
                        initial={shouldReduceMotion ? { opacity: 1 } : { opacity: 0, x: -8, scale: 0.96 }}
                        animate={shouldReduceMotion ? { opacity: 1 } : { opacity: 1, x: 0, scale: 1 }}
                        exit={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, x: -8, scale: 0.96 }}
                        transition={{ duration: 0.15 }}
                        className="fixed left-[72px] top-28 w-80 bg-[#0e0c1e]/95 backdrop-blur-2xl rounded-2xl border border-white/20 p-3.5 shadow-[0_15px_50px_rgba(0,0,0,0.85)] z-50 text-xs"
                      >
                        <div className="flex items-center justify-between pb-2 border-b border-white/10 mb-2">
                          <span className="font-semibold text-slate-200">Search Chats</span>
                          <button
                            type="button"
                            onClick={() => setCollapsedSearchOpen(false)}
                            className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-white/10"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </div>
                        <div className="relative flex items-center mb-2">
                          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 pointer-events-none" />
                          <input
                            type="text"
                            value={sessionSearch}
                            onChange={(e) => setSessionSearch(e.target.value)}
                            placeholder="Type to filter..."
                            autoFocus
                            className="w-full bg-white/[0.06] border border-white/10 rounded-lg pl-8 pr-2.5 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-violet-500/50"
                          />
                        </div>
                        <div className="max-h-56 overflow-y-auto space-y-1 pr-1 custom-scrollbar">
                          {filteredSessions.length === 0 ? (
                            <p className="text-slate-500 text-center py-3 text-[11px]">No matching chats</p>
                          ) : (
                            filteredSessions.map((s) => (
                              <button
                                key={s.id}
                                type="button"
                                onClick={() => {
                                  handleSelectSession(s.id);
                                  setCollapsedSearchOpen(false);
                                }}
                                className={`w-full text-left px-3 py-2 rounded-xl truncate transition-colors flex items-center gap-2 ${
                                  s.id === activeSessionId
                                    ? 'bg-violet-600/30 text-white font-medium border border-violet-500/30'
                                    : 'text-slate-300 hover:text-white hover:bg-white/10'
                                }`}
                              >
                                <MessageSquare className="w-3.5 h-3.5 shrink-0 text-violet-400" />
                                <span className="truncate">{s.title || 'New Chat'}</span>
                              </button>
                            ))
                          )}
                        </div>
                      </m.div>
                    </>
                  )}
                </AnimatePresence>
              </div>
            </div>

            <div className="flex flex-col items-center gap-3 w-full">
              <m.button
                type="button"
                whileHover={shouldReduceMotion ? {} : { scale: 1.08 }}
                whileTap={shouldReduceMotion ? {} : { scale: 0.92 }}
                onClick={() => setSettingsOpen(true)}
                title="Settings"
                className="w-9 h-9 rounded-xl bg-white/[0.04] hover:bg-white/[0.1] text-slate-400 hover:text-violet-300 border border-white/10 flex items-center justify-center transition-colors cursor-pointer"
              >
                <Settings className="w-4 h-4" />
              </m.button>

              <m.button
                type="button"
                whileHover={shouldReduceMotion ? {} : { scale: 1.08 }}
                whileTap={shouldReduceMotion ? {} : { scale: 0.92 }}
                onClick={() => navigate('/account/add-face')}
                title="Biometric Face ID"
                className="w-9 h-9 rounded-xl bg-white/[0.04] hover:bg-indigo-600/20 text-slate-400 hover:text-indigo-300 border border-white/10 flex items-center justify-center transition-colors cursor-pointer"
              >
                <Camera className="w-4 h-4" />
              </m.button>

              <div
                title={user}
                className="w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-600 to-indigo-500 flex items-center justify-center text-white font-semibold text-xs shadow-xs"
              >
                {user ? user.charAt(0).toUpperCase() : 'U'}
              </div>

              <button
                type="button"
                onClick={() => {
                  setSidebarCollapsed(false);
                  localStorage.setItem('omnirag_sidebar_collapsed', 'false');
                }}
                title="Expand sidebar"
                className="p-1.5 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-white/5 transition-colors cursor-pointer"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        ) : (
          /* Expanded Full Sidebar Content */
          <div className="w-72 lg:w-80 flex flex-col h-full shrink-0 overflow-hidden">
            <div className="p-4 border-b border-white/10 flex items-center justify-between">
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
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => {
                    setSidebarCollapsed(true);
                    localStorage.setItem('omnirag_sidebar_collapsed', 'true');
                  }}
                  title="Collapse sidebar"
                  className="hidden md:flex p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-white/10 transition-colors cursor-pointer"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setSidebarOpen(false)}
                  className="md:hidden p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* "+ New Chat" Button & Search Bar */}
            <div className="p-3 border-b border-white/10 space-y-2">
              <m.button
                whileHover={shouldReduceMotion ? {} : { scale: 1.02 }}
                whileTap={shouldReduceMotion ? {} : { scale: 0.97 }}
                transition={{ duration: 0.15 }}
                onClick={handleCreateNewSession}
                className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-violet-600 hover:bg-violet-500 text-white font-medium text-xs sm:text-sm shadow-md shadow-violet-600/25 transition-colors cursor-pointer"
              >
                <Plus className="w-4 h-4 stroke-[2.5]" />
                <span>New Chat</span>
              </m.button>

              <div className="relative flex items-center">
                <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 pointer-events-none" />
                <input
                  type="text"
                  value={sessionSearch}
                  onChange={(e) => setSessionSearch(e.target.value)}
                  placeholder="Search chats..."
                  className="w-full pl-8 pr-7 py-1.5 rounded-xl bg-white/[0.05] hover:bg-white/[0.08] focus:bg-white/[0.1] border border-white/10 focus:border-violet-500/50 focus:outline-none text-xs text-slate-200 placeholder-slate-500 transition-all"
                />
                {sessionSearch && (
                  <button
                    type="button"
                    onClick={() => setSessionSearch('')}
                    className="absolute right-2 text-slate-400 hover:text-slate-200 p-0.5 rounded cursor-pointer"
                    title="Clear search"
                  >
                    <X className="w-3 h-3" />
                  </button>
                )}
              </div>
            </div>

            {/* Sessions History List */}
            <div className="flex-1 overflow-y-auto px-2 py-3 space-y-1 scrollbar-thin scrollbar-thumb-slate-700">
              <div className="px-2 py-1 flex items-center justify-between text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                <span>Conversations</span>
                <span className="text-[10px] bg-slate-800 px-1.5 py-0.5 rounded text-slate-300 font-mono">
                  {filteredSessions.length}
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
              ) : filteredSessions.length === 0 ? (
                <div className="p-4 text-center text-slate-400 text-xs space-y-2">
                  <SearchX className="w-5 h-5 mx-auto text-slate-500" />
                  <p className="text-slate-400">No chats matching &quot;{sessionSearch}&quot;</p>
                  <button
                    type="button"
                    onClick={() => setSessionSearch('')}
                    className="px-2.5 py-1 text-[11px] rounded-lg bg-white/10 hover:bg-white/15 text-violet-300 hover:text-violet-200 transition-colors cursor-pointer"
                  >
                    Clear search
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  {filteredSessions.filter((s) => s.pinned).length > 0 && (
                    <div>
                      <div className="px-2 py-1 flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-violet-400">
                        <span className="flex items-center gap-1.5">
                          <Pin className="w-3 h-3 fill-violet-400 text-violet-400" />
                          <span>Pinned</span>
                        </span>
                        <span className="text-[10px] bg-violet-950/60 border border-violet-500/30 text-violet-300 px-1.5 py-0.2 rounded font-mono">
                          {filteredSessions.filter((s) => s.pinned).length}
                        </span>
                      </div>
                      <div className="space-y-0.5 mt-1">
                        {filteredSessions
                          .filter((s) => s.pinned)
                          .map((sess) => renderSessionItem(sess))}
                      </div>
                    </div>
                  )}
                  {filteredSessions.filter((s) => !s.pinned).length > 0 && (
                    <div>
                      <div className="px-2 py-1 flex items-center justify-between text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                        <span>{filteredSessions.some((s) => s.pinned) ? 'Recent' : 'Conversations'}</span>
                        <span className="text-[10px] bg-slate-800 text-slate-400 px-1.5 py-0.2 rounded font-mono">
                          {filteredSessions.filter((s) => !s.pinned).length}
                        </span>
                      </div>
                      <div className="space-y-0.5 mt-1">
                        {filteredSessions
                          .filter((s) => !s.pinned)
                          .map((sess) => renderSessionItem(sess))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Sidebar Footer: Single source for user identity, settings, and sign-out */}
            <div className="p-3 shrink-0">
              <div className="p-3 rounded-2xl bg-white/[0.05] hover:bg-white/[0.07] border border-white/10 backdrop-blur-xl shadow-lg shadow-black/25 space-y-2.5 transition-all">
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className="relative w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-600 via-violet-600 to-indigo-500 flex items-center justify-center text-white font-bold text-xs shrink-0 shadow-md shadow-violet-600/30">
                      {user ? user.charAt(0).toUpperCase() : 'U'}
                      {loginMethod === 'face' && (
                        <span
                          title="Logged in via Face Recognition"
                          className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-emerald-400 ring-2 ring-slate-900 shadow-xs"
                        />
                      )}
                    </div>
                    <div className="min-w-0">
                      <p className="truncate font-semibold text-slate-100 text-xs leading-none">{user}</p>
                      <p className="text-[10px] text-slate-400 mt-1 flex items-center gap-1">
                        {loginMethod === 'face' ? (
                          <span className="text-emerald-400 font-medium flex items-center gap-1">
                            <ScanFace className="w-3 h-3 text-emerald-400" /> Face ID Verified
                          </span>
                        ) : (
                          <span className="text-indigo-300 font-medium flex items-center gap-1">
                            <ShieldCheck className="w-3 h-3 text-indigo-400" /> Password Verified
                          </span>
                        )}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={() => setSettingsOpen(true)}
                      title="Settings"
                      className="p-1.5 rounded-xl text-slate-400 hover:text-white hover:bg-white/10 border border-transparent hover:border-white/10 transition-all cursor-pointer"
                    >
                      <Settings className="w-4 h-4 text-violet-400" />
                    </button>
                    <button
                      type="button"
                      onClick={() => navigate('/account/add-face')}
                      title="Biometric Face Login Settings"
                      className="p-1.5 rounded-xl text-slate-400 hover:text-white hover:bg-white/10 border border-transparent hover:border-white/10 transition-all cursor-pointer"
                    >
                      <Camera className="w-4 h-4 text-indigo-400" />
                    </button>
                  </div>
                </div>

                <div className="border-t border-white/[0.08]" />

                <button
                  type="button"
                  onClick={handleLogout}
                  className="w-full flex items-center justify-center gap-2 py-1.5 px-3 rounded-xl text-xs font-medium text-slate-300 hover:text-rose-300 hover:bg-rose-500/10 border border-white/[0.06] hover:border-rose-500/30 transition-all cursor-pointer"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  <span>Sign Out</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </aside>
    </>
  );
};

export default ChatSidebar;
