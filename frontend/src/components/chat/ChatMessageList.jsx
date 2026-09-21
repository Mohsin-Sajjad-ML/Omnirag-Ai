import React, { useState, useEffect, useRef, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { m, AnimatePresence } from 'motion/react';
import {
  Menu,
  ChevronDown,
  Sparkles,
  X,
  ScanFace,
  ShieldCheck,
  Settings,
  Camera,
  LogOut,
  Code,
  Compass,
  FileText,
  User,
  Pencil,
  Bot,
  Globe,
  AlertCircle,
  AlertTriangle,
  SearchX,
  RefreshCw,
  Loader2,
  CheckCircle2,
  Download,
} from 'lucide-react';

/**
 * ProgressiveText - Progressively reveals assistant responses word-by-word
 * instead of popping in all at once.
 */
const markdownComponents = {
  h1: ({ children, ...props }) => (
    <h1 className="text-base sm:text-lg font-bold text-white mt-4 mb-2 pb-1 border-b border-white/10 tracking-tight" {...props}>
      {children}
    </h1>
  ),
  h2: ({ children, ...props }) => (
    <h2 className="text-sm sm:text-base font-bold text-violet-200 mt-3.5 mb-1.5 tracking-tight" {...props}>
      {children}
    </h2>
  ),
  h3: ({ children, ...props }) => (
    <h3 className="text-xs sm:text-sm font-bold text-violet-300 mt-3 mb-1.5 flex items-center gap-1.5" {...props}>
      {children}
    </h3>
  ),
  h4: ({ children, ...props }) => (
    <h4 className="text-xs font-semibold text-slate-200 mt-2.5 mb-1" {...props}>
      {children}
    </h4>
  ),
  p: ({ children, ...props }) => (
    <p className="text-xs sm:text-sm text-slate-200 leading-relaxed mb-2.5 last:mb-0" {...props}>
      {children}
    </p>
  ),
  ul: ({ children, ...props }) => (
    <ul className="list-disc list-outside ml-4 sm:ml-5 space-y-1 mb-2.5 text-xs sm:text-sm text-slate-200 marker:text-violet-400" {...props}>
      {children}
    </ul>
  ),
  ol: ({ children, ...props }) => (
    <ol className="list-decimal list-outside ml-4 sm:ml-5 space-y-1 mb-2.5 text-xs sm:text-sm text-slate-200 marker:text-violet-400" {...props}>
      {children}
    </ol>
  ),
  li: ({ children, ...props }) => (
    <li className="leading-relaxed pl-1" {...props}>
      {children}
    </li>
  ),
  strong: ({ children, ...props }) => (
    <strong className="font-semibold text-white tracking-wide" {...props}>
      {children}
    </strong>
  ),
  em: ({ children, ...props }) => (
    <em className="italic text-violet-200" {...props}>
      {children}
    </em>
  ),
  hr: ({ ...props }) => (
    <hr className="my-3.5 border-t border-white/15" {...props} />
  ),
  blockquote: ({ children, ...props }) => (
    <blockquote className="border-l-2 border-violet-500/60 pl-3 py-1 my-2.5 text-slate-300 italic bg-white/[0.03] rounded-r-lg" {...props}>
      {children}
    </blockquote>
  ),
  code: ({ inline, className, children, ...props }) => {
    if (inline) {
      return (
        <code className="px-1.5 py-0.5 rounded-md bg-white/10 font-mono text-[11px] text-violet-300 border border-white/10" {...props}>
          {children}
        </code>
      );
    }
    return (
      <code className="font-mono text-[11px] text-slate-200" {...props}>
        {children}
      </code>
    );
  },
  pre: ({ children, ...props }) => (
    <pre className="my-2.5 p-3.5 rounded-xl bg-[#0a0815] border border-white/15 overflow-x-auto text-[11px] font-mono text-slate-200 shadow-inner" {...props}>
      {children}
    </pre>
  ),
  table: ({ children, ...props }) => (
    <div className="overflow-x-auto my-3 rounded-xl border border-white/15 shadow-sm">
      <table className="w-full text-left text-xs border-collapse" {...props}>
        {children}
      </table>
    </div>
  ),
  thead: ({ children, ...props }) => (
    <thead className="bg-white/[0.08] text-violet-300 border-b border-white/15 font-semibold" {...props}>
      {children}
    </thead>
  ),
  tbody: ({ children, ...props }) => (
    <tbody className="divide-y divide-white/10 text-slate-200" {...props}>
      {children}
    </tbody>
  ),
  tr: ({ children, ...props }) => (
    <tr className="hover:bg-white/[0.04] transition-colors" {...props}>
      {children}
    </tr>
  ),
  th: ({ children, ...props }) => (
    <th className="px-3 py-2 font-semibold text-xs text-violet-300" {...props}>
      {children}
    </th>
  ),
  td: ({ children, ...props }) => (
    <td className="px-3 py-2 text-xs" {...props}>
      {children}
    </td>
  ),
  a: ({ children, ...props }) => (
    <a className="text-violet-400 hover:text-violet-300 underline underline-offset-2 transition-colors cursor-pointer" target="_blank" rel="noopener noreferrer" {...props}>
      {children}
    </a>
  ),
};

export const ProgressiveText = React.memo(({ content, shouldAnimate, shouldReduceMotion, onScroll, onComplete }) => {
  const words = useMemo(() => {
    if (!content) return [];
    return content.split(/(\s+)/);
  }, [content]);

  const hasAnimatedRef = useRef(false);

  const [revealedIndex, setRevealedIndex] = useState(() => {
    return !shouldAnimate || shouldReduceMotion ? null : 1;
  });

  const onScrollRef = useRef(onScroll);
  useEffect(() => {
    onScrollRef.current = onScroll;
  });

  const onCompleteRef = useRef(onComplete);
  useEffect(() => {
    onCompleteRef.current = onComplete;
  });

  useEffect(() => {
    if (!shouldAnimate || shouldReduceMotion || hasAnimatedRef.current) {
      setRevealedIndex(null);
      return;
    }

    hasAnimatedRef.current = true;
    setRevealedIndex(1);
    let current = 1;
    const total = words.length;

    const interval = setInterval(() => {
      current += 2;
      if (current >= total) {
        setRevealedIndex(null);
        clearInterval(interval);
        if (onCompleteRef.current) onCompleteRef.current();
      } else {
        setRevealedIndex(current);
        if (onScrollRef.current) onScrollRef.current();
      }
    }, 18);

    return () => clearInterval(interval);
  }, [shouldAnimate, shouldReduceMotion, words]);

  const displayedContent = useMemo(() => {
    if (revealedIndex === null) return content;
    return words.slice(0, revealedIndex).join('');
  }, [content, words, revealedIndex]);

  return (
    <div className="w-full text-xs sm:text-sm leading-relaxed overflow-x-auto [&>*:first-child]:mt-0 [&>*:last-child]:mb-0">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
        {displayedContent}
      </ReactMarkdown>
    </div>
  );
});

export const ChatMessageList = ({
  setSidebarOpen,
  activeSessionObj,
  activeSessionId,
  sessions,
  documents,
  setDocSelectorOpen,
  handleExportSession,
  loadingMessages,
  messages,
  inlineEvents,
  shouldReduceMotion,
  setInputQuery,
  editingMessageId,
  setEditingMessageId,
  editingMessageContent,
  setEditingMessageContent,
  handleEditUserMessage,
  scrollToBottom,
  handleRevealComplete,
  activeCitation,
  setActiveCitation,
  isSending,
  handleRegenerateLastAssistantMessage,
  messagesEndRef,
}) => {
  const [exportMenuOpen, setExportMenuOpen] = useState(false);
  const exportMenuRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(e) {
      if (exportMenuRef.current && !exportMenuRef.current.contains(e.target)) {
        setExportMenuOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <>
      {/* Top Header Bar — Borderless, transparent, seamless on nebula background */}
      <header className="h-14 px-4 sm:px-6 md:px-8 flex items-center justify-between shrink-0 z-20 bg-transparent">
        <div className="flex items-center gap-3 min-w-0">
          <button
            onClick={() => setSidebarOpen(true)}
            className="md:hidden p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-white/10 cursor-pointer transition-colors"
          >
            <Menu className="w-5 h-5" />
          </button>

          <div
            title="OmniRAG 4.0e Neural Engine with Grounded Retrieval"
            className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/[0.06] hover:bg-white/[0.1] border border-white/10 text-xs font-medium text-slate-200 shadow-xs transition-colors backdrop-blur-md cursor-default select-none shrink-0"
          >
            <span className="w-2 h-2 rounded-full bg-violet-400 animate-pulse" />
            <span className="font-semibold tracking-tight">OmniRAG 4.0e</span>
            <ChevronDown className="w-3 h-3 text-slate-400" />
          </div>

          <div className="min-w-0 hidden sm:block">
            <h2 className="font-semibold text-xs text-slate-300 truncate">
              {activeSessionObj?.title || (sessions.length > 0 ? 'OmniRAG Chat' : 'New Conversation')}
            </h2>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={() => setDocSelectorOpen((prev) => !prev)}
            className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/[0.04] hover:bg-white/[0.08] border border-white/10 text-[11px] text-slate-300 transition-colors cursor-pointer backdrop-blur-md shadow-xs"
            title="Knowledge Base Documents"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span>{documents.length} doc{documents.length === 1 ? '' : 's'}</span>
          </button>

          {/* Export Chat Menu in Top-Right Corner (Replaces duplicate user menu) */}
          <div className="relative" ref={exportMenuRef}>
            <button
              type="button"
              onClick={() => setExportMenuOpen((prev) => !prev)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/[0.06] hover:bg-white/[0.12] border border-white/10 hover:border-violet-500/30 text-xs font-medium text-slate-200 transition-all cursor-pointer shadow-xs backdrop-blur-md"
              title="Export this conversation as PDF or plain text"
            >
              <Download className="w-3.5 h-3.5 text-violet-400" />
              <span>Export</span>
              <ChevronDown
                className={`w-3 h-3 text-slate-400 transition-transform duration-200 ${
                  exportMenuOpen ? 'rotate-180' : ''
                }`}
              />
            </button>

            {exportMenuOpen && (
              <div className="absolute right-0 mt-2 w-48 glass-panel bg-[#120f24]/95 border border-white/15 rounded-2xl shadow-2xl p-1.5 z-50 text-xs backdrop-blur-xl">
                <div className="px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400 border-b border-white/10 mb-1">
                  Export Conversation
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setExportMenuOpen(false);
                    const sid = activeSessionId || activeSessionObj?.id;
                    if (handleExportSession && sid) {
                      handleExportSession(sid, 'pdf');
                    } else {
                      alert('Select or create a conversation to export.');
                    }
                  }}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-slate-200 hover:text-white hover:bg-white/10 transition-colors text-left cursor-pointer"
                >
                  <FileText className="w-3.5 h-3.5 text-violet-400" />
                  <span>Export as PDF</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setExportMenuOpen(false);
                    const sid = activeSessionId || activeSessionObj?.id;
                    if (handleExportSession && sid) {
                      handleExportSession(sid, 'txt');
                    } else {
                      alert('Select or create a conversation to export.');
                    }
                  }}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-slate-200 hover:text-white hover:bg-white/10 transition-colors text-left cursor-pointer"
                >
                  <FileText className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Export as Plain Text</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Scrollable Chat Message History (Sitting directly on nebula/glass background) */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden min-w-0 px-4 sm:px-6 md:px-8 py-4 space-y-4 scrollbar-thin scrollbar-thumb-slate-800">
        <div className="w-full max-w-[820px] mx-auto space-y-6">
        {loadingMessages ? (
          <div className="h-full flex items-center justify-center text-slate-500 text-xs gap-2">
            <Loader2 className="w-4 h-4 animate-spin text-indigo-500" />
            <span>Loading messages...</span>
          </div>
        ) : messages.length === 0 && inlineEvents.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center max-w-2xl mx-auto px-4 py-8 space-y-6">
            <m.div
              initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.85 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={shouldReduceMotion ? { duration: 0 } : { type: 'spring', stiffness: 320, damping: 22 }}
              className="relative flex items-center justify-center my-2"
            >
              <div
                className={`absolute w-24 h-24 sm:w-28 sm:h-28 rounded-full bg-gradient-to-tr from-violet-600 via-fuchsia-500 to-cyan-400 blur-2xl ${
                  shouldReduceMotion ? 'opacity-40' : 'opacity-60 pulse-glow-circle'
                }`}
              />
              <div className="relative w-16 h-16 sm:w-20 sm:h-20 rounded-full bg-gradient-to-tr from-violet-500 via-fuchsia-500 to-purple-600 p-0.5 shadow-2xl shadow-fuchsia-500/40 flex items-center justify-center overflow-hidden">
                <div className="w-full h-full rounded-full bg-[#0a0818] relative flex items-center justify-center overflow-hidden">
                  <div
                    className="absolute inset-0 bg-[radial-gradient(circle_at_30%_30%,rgba(217,70,239,0.85),transparent_55%),radial-gradient(circle_at_70%_70%,rgba(6,182,212,0.65),transparent_55%)] animate-spin"
                    style={{ animationDuration: '24s' }}
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-transparent to-white/20" />
                  <Sparkles className="w-7 h-7 sm:w-8 sm:h-8 text-white drop-shadow-[0_0_8px_rgba(255,255,255,0.85)] relative z-10" />
                </div>
              </div>
            </m.div>

            <m.div
              initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={shouldReduceMotion ? { duration: 0 } : { type: 'spring', stiffness: 350, damping: 25, delay: 0.05 }}
              className="space-y-2 max-w-lg"
            >
              <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
                Welcome to your cognitive co-pilot
              </h2>
              <p className="text-xs sm:text-sm text-slate-400 leading-relaxed">
                I am OmniRAG. You can ask me to write, code, plan, or explore any idea grounded in your knowledge base.
              </p>
            </m.div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 w-full pt-1">
              {[
                {
                  title: "Explain this Code",
                  desc: "\"Can you find the bug in this snippet and explain how it works?\"",
                  prompt: "Can you find the bug in this snippet and explain how it works?",
                  icon: Code,
                  iconColor: "text-violet-400",
                },
                {
                  title: "Plan a Project",
                  desc: "\"Create a 5-day, budget-friendly milestone plan...\"",
                  prompt: "Create a 5-day, budget-friendly milestone plan...",
                  icon: Compass,
                  iconColor: "text-fuchsia-400",
                },
                {
                  title: "Brainstorm Ideas",
                  desc: "\"I want to explore innovative approaches and concepts for...\"",
                  prompt: "I want to explore innovative approaches and concepts for...",
                  icon: Sparkles,
                  iconColor: "text-cyan-400",
                },
              ].map((card, idx) => {
                const Icon = card.icon;
                return (
                  <m.button
                    key={card.title}
                    type="button"
                    onClick={() => setInputQuery(card.prompt)}
                    initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={
                      shouldReduceMotion
                        ? { duration: 0 }
                        : { type: 'spring', stiffness: 350, damping: 25, delay: 0.08 + idx * 0.05 }
                    }
                    whileHover={shouldReduceMotion ? {} : { scale: 1.02, y: -2 }}
                    whileTap={shouldReduceMotion ? {} : { scale: 0.98 }}
                    className="glass-panel p-4 rounded-2xl text-left border border-white/10 hover:border-violet-500/40 bg-white/[0.03] hover:bg-white/[0.07] hover:shadow-xl transition-all group cursor-pointer flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        <Icon className={`w-4 h-4 ${card.iconColor}`} />
                        <h4 className="text-xs sm:text-sm font-semibold text-slate-200 group-hover:text-white transition-colors">
                          {card.title}
                        </h4>
                      </div>
                      <p className="text-[11px] text-slate-400 leading-relaxed italic">
                        {card.desc}
                      </p>
                    </div>
                  </m.button>
                );
              })}
            </div>

            {documents.length > 0 && (
              <m.div
                initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={shouldReduceMotion ? { duration: 0 } : { delay: 0.25 }}
                className="w-full glass-panel border border-white/10 rounded-xl p-3 text-left max-w-lg mt-2"
              >
                <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block"></span>
                  <span>Ready in Knowledge Base ({documents.length}):</span>
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {documents.slice(0, 4).map((doc) => (
                    <span
                      key={doc.id}
                      className="inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded-md glass-panel border border-white/10 text-slate-300"
                    >
                      <FileText className="w-3 h-3 text-violet-400" />
                      <span className="truncate max-w-[130px]">{doc.original_filename}</span>
                    </span>
                  ))}
                  {documents.length > 4 && (
                    <span className="text-[11px] text-slate-500 self-center">
                      +{documents.length - 4} more
                    </span>
                  )}
                </div>
              </m.div>
            )}
          </div>
        ) : (
          <>
            {messages.map((msg, idx) => {
              const isUser = msg.role === 'user';
              const isError = msg.is_error;
              const isFallback = msg.is_fallback && !isError;

              if (isUser) {
                return (
                  <m.div
                    initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={
                      shouldReduceMotion
                        ? { duration: 0 }
                        : { type: 'spring', stiffness: 350, damping: 26, mass: 0.8, delay: Math.min(idx * 0.04, 0.4) }
                    }
                    key={msg.id}
                    className="flex justify-end items-end gap-2"
                  >
                    <div className="max-w-full sm:max-w-[700px] md:max-w-[760px] min-w-0 break-words [overflow-wrap:anywhere] overflow-hidden glass-panel bg-violet-600/80 backdrop-blur text-white rounded-2xl rounded-br-xs px-4 py-3 text-xs sm:text-sm shadow-sm leading-relaxed whitespace-pre-wrap border border-violet-500/50 group/msg relative">
                      {editingMessageId === msg.id ? (
                        <div className="flex flex-col gap-2 w-full min-w-[200px]">
                          <textarea
                            autoFocus
                            value={editingMessageContent}
                            onChange={(e) => setEditingMessageContent(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault();
                                handleEditUserMessage(msg.id);
                              } else if (e.key === 'Escape') {
                                setEditingMessageId(null);
                              }
                            }}
                            className="w-full bg-slate-900 border border-indigo-500/50 text-white rounded-lg p-2 text-xs outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 min-h-[60px]"
                          />
                          <div className="flex items-center justify-end gap-2">
                            <button onClick={() => setEditingMessageId(null)} className="text-xs text-slate-400 hover:text-white px-2 py-1 cursor-pointer">Cancel</button>
                            <button onClick={() => handleEditUserMessage(msg.id)} className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs px-3 py-1 rounded shadow cursor-pointer">Save & Submit</button>
                          </div>
                        </div>
                      ) : (
                        <>
                          {msg.content}
                          <button
                            onClick={() => { setEditingMessageId(msg.id); setEditingMessageContent(msg.content); }}
                            className="absolute -right-8 top-0 p-1.5 opacity-0 group-hover/msg:opacity-100 text-slate-400 hover:text-white transition-opacity bg-slate-800/80 rounded-lg shadow-sm cursor-pointer"
                            title="Edit message"
                          >
                            <Pencil className="w-3 h-3" />
                          </button>
                        </>
                      )}
                    </div>
                    <div className="w-6 h-6 rounded-full glass-panel border border-white/10 flex items-center justify-center text-slate-300 shrink-0 text-[10px]">
                      <User className="w-3.5 h-3.5" />
                    </div>
                  </m.div>
                );
              }

              return (
                <m.div
                  initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={
                    shouldReduceMotion
                      ? { duration: 0 }
                      : { type: 'spring', stiffness: 350, damping: 26, mass: 0.8, delay: Math.min(idx * 0.04, 0.4) }
                  }
                  key={msg.id}
                  className="flex justify-start items-start gap-3 w-full min-w-0"
                >
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
                      w-fit max-w-[calc(100%-44px)] sm:max-w-[88%] min-w-0 rounded-2xl rounded-tl-xs px-4 py-3 sm:px-5 sm:py-3.5 text-xs sm:text-sm shadow-sm leading-relaxed break-words [overflow-wrap:anywhere] overflow-hidden
                      ${
                        isError
                          ? 'glass-panel border border-rose-500/30 text-rose-200'
                          : isFallback
                          ? 'glass-panel border border-amber-500/30 text-slate-300'
                          : 'glass-panel border border-white/10 text-slate-200'
                      }
                    `}
                  >
                    {isError && (
                      <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-rose-500/10 border border-rose-500/25 text-rose-400 mb-2">
                        <AlertCircle className="w-3 h-3" />
                        <span>Connection Error</span>
                      </div>
                    )}

                    {!isError && (
                      <div className="mb-2 flex items-center gap-1.5 flex-wrap">
                        {msg.source === 'rag' ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-medium bg-violet-500/10 border border-violet-500/25 text-violet-300 select-none">
                            <FileText className="w-2.5 h-2.5 text-violet-400" />
                            <span>From your documents</span>
                          </span>
                        ) : msg.source === 'rag_and_web' || msg.source === 'hybrid' ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-medium bg-gradient-to-r from-violet-500/15 via-fuchsia-500/15 to-violet-500/15 border border-fuchsia-500/30 text-fuchsia-200 select-none">
                            <FileText className="w-2.5 h-2.5 text-violet-400" />
                            <span className="text-white/40">+</span>
                            <Globe className="w-2.5 h-2.5 text-fuchsia-400" />
                            <span>Documents + Web Search</span>
                          </span>
                        ) : msg.source === 'web_search' ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-medium bg-fuchsia-500/10 border border-fuchsia-500/25 text-fuchsia-300 select-none">
                            <Globe className="w-2.5 h-2.5 text-fuchsia-400" />
                            <span>From web search</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-medium bg-white/5 border border-white/10 text-slate-300 select-none">
                            <Sparkles className="w-2.5 h-2.5 text-amber-400" />
                            <span>General knowledge</span>
                          </span>
                        )}

                        {isFallback && (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-medium bg-amber-500/10 border border-amber-500/25 text-amber-400 select-none">
                            <SearchX className="w-2.5 h-2.5" />
                            <span>Not Found in Context</span>
                          </span>
                        )}
                      </div>
                    )}

                    <ProgressiveText
                      content={msg.content}
                      shouldAnimate={Boolean(msg.animateReveal)}
                      shouldReduceMotion={shouldReduceMotion}
                      onScroll={scrollToBottom}
                      onComplete={() => handleRevealComplete(msg.id)}
                    />

                    {!isFallback && msg.citations && msg.citations.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-white/10 space-y-1.5">
                        <p className="text-[10px] uppercase font-bold tracking-wider text-violet-400 flex items-center gap-1">
                          <span>Sources &amp; Citations</span>
                        </p>
                        <div className="flex flex-wrap gap-1.5">
                          {msg.citations.map((c, i) => {
                            const chunks = c.chunk_references || [];
                            const chunkStr = chunks.length > 0 ? ` (chunk${chunks.length > 1 ? 's' : ''} ${chunks.join(', ')})` : '';
                            const citationKey = `citation-${msg.id}-${i}`;
                            return (
                              <m.button
                                key={i}
                                type="button"
                                layoutId={shouldReduceMotion ? undefined : citationKey}
                                onClick={() => setActiveCitation({ ...c, msgId: msg.id, index: i, key: citationKey })}
                                whileHover={shouldReduceMotion ? {} : { scale: 1.03 }}
                                whileTap={shouldReduceMotion ? {} : { scale: 0.97 }}
                                className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px] glass-panel border border-violet-500/30 hover:border-violet-500/60 text-violet-300 hover:text-white font-medium cursor-pointer shadow-sm transition-colors text-left"
                              >
                                <FileText className="w-3 h-3 text-violet-400 shrink-0" />
                                <span className="truncate max-w-[180px]">{c.filename}</span>
                                <span className="text-[10px] text-violet-400/80">{chunkStr}</span>
                              </m.button>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {!isFallback && msg.low_context && (
                      <div className="mt-2.5">
                        <span className="inline-flex items-center gap-1 text-[11px] font-medium text-amber-400/90 bg-amber-500/10 border border-amber-500/25 px-2 py-0.5 rounded-full">
                          <AlertTriangle className="w-3 h-3 text-amber-400" />
                          <span>Limited context: Answer synthesized from fewer source chunks.</span>
                        </span>
                      </div>
                    )}

                    {(() => {
                      const lastAssistant = messages.slice().reverse().find((m) => m.role === 'assistant');
                      const isLastAssistant = msg.id === lastAssistant?.id;
                      if (!isLastAssistant) return null;

                      return (
                        <div className="mt-3 pt-2.5 border-t border-white/10 flex items-center justify-end">
                          <m.button
                            type="button"
                            whileHover={shouldReduceMotion ? {} : { scale: 1.05 }}
                            whileTap={shouldReduceMotion ? {} : { scale: 0.95 }}
                            transition={{ duration: 0.15 }}
                            disabled={isSending}
                            onClick={handleRegenerateLastAssistantMessage}
                            title="Regenerate assistant answer"
                            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg glass-panel bg-white/5 hover:bg-violet-600/20 text-slate-300 hover:text-violet-200 border border-white/10 hover:border-violet-500/40 text-[11px] font-medium transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            <RefreshCw className={`w-3 h-3 text-violet-400 ${isSending ? 'animate-spin' : ''}`} />
                            <span>Regenerate</span>
                          </m.button>
                        </div>
                      );
                    })()}
                  </div>
                </m.div>
              );
            })}

            {inlineEvents.map((ev) => (
              <div key={ev.id} className="flex justify-center my-2">
                <div
                  className={`
                    inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-medium shadow-sm transition-all
                    ${
                      ev.status === 'uploading'
                        ? 'glass-panel border border-indigo-500/40 text-indigo-300'
                        : ev.status === 'success'
                        ? 'glass-panel border border-emerald-500/40 text-emerald-300'
                        : 'glass-panel border border-rose-500/40 text-rose-300'
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

            {isSending && (
              <m.div
                initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={
                  shouldReduceMotion
                    ? { duration: 0 }
                    : { type: 'spring', stiffness: 350, damping: 25 }
                }
                className="flex justify-start items-start gap-3"
              >
                <div className="w-7 h-7 rounded-xl bg-violet-600/20 border border-violet-500/40 flex items-center justify-center text-violet-400 shadow-sm shrink-0 mt-0.5">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="max-w-md w-full glass-panel border border-violet-500/25 rounded-2xl rounded-tl-xs p-4 shadow-xl relative overflow-hidden space-y-3">
                  {!shouldReduceMotion && <div className="shimmer-sweep-overlay pointer-events-none" />}
                  <div className="flex items-center gap-2 text-xs font-medium text-violet-300">
                    <Sparkles className="w-3.5 h-3.5 text-fuchsia-400 animate-spin" style={{ animationDuration: '3s' }} />
                    <span>Synthesizing response from knowledge base...</span>
                  </div>
                  <div className="space-y-2 pt-0.5">
                    <div className="h-2.5 bg-white/10 rounded-full w-5/6 overflow-hidden relative">
                      {!shouldReduceMotion && <div className="shimmer-sweep-overlay pointer-events-none" />}
                    </div>
                    <div className="h-2.5 bg-white/10 rounded-full w-full overflow-hidden relative">
                      {!shouldReduceMotion && <div className="shimmer-sweep-overlay pointer-events-none" />}
                    </div>
                    <div className="h-2.5 bg-white/10 rounded-full w-3/5 overflow-hidden relative">
                      {!shouldReduceMotion && <div className="shimmer-sweep-overlay pointer-events-none" />}
                    </div>
                  </div>
                </div>
              </m.div>
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>
    </div>

      {/* Citation Detail Modal */}
      <AnimatePresence>
        {activeCitation && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <m.div
              initial={shouldReduceMotion ? { opacity: 1 } : { opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={shouldReduceMotion ? { opacity: 0 } : { opacity: 0 }}
              className="fixed inset-0 bg-black/70 backdrop-blur-sm"
              onClick={() => setActiveCitation(null)}
            />

            <m.div
              layoutId={shouldReduceMotion ? undefined : activeCitation.key}
              initial={shouldReduceMotion ? { opacity: 1 } : { opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.95 }}
              transition={
                shouldReduceMotion
                  ? { duration: 0 }
                  : { type: 'spring', stiffness: 350, damping: 26, mass: 0.8 }
              }
              className="relative z-10 w-full max-w-lg glass-panel border border-violet-500/30 rounded-2xl p-5 shadow-2xl bg-[#0e0c1e]/98 text-left text-slate-200"
            >
              <div className="flex items-start justify-between gap-3 border-b border-white/10 pb-3">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-9 h-9 rounded-xl bg-violet-600/20 border border-violet-500/30 flex items-center justify-center text-violet-400 shrink-0 shadow-sm">
                    <FileText className="w-4 h-4" />
                  </div>
                  <div className="min-w-0">
                    <h4 className="text-sm font-semibold text-white truncate">
                      {activeCitation.filename}
                    </h4>
                    <p className="text-[11px] text-violet-300/80 font-medium">
                      {activeCitation.chunk_references?.length > 0
                        ? `Referenced Chunks: ${activeCitation.chunk_references.join(', ')}`
                        : 'Source Document in Knowledge Base'}
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setActiveCitation(null)}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="mt-4 space-y-3">
                <div className="text-xs text-slate-300 space-y-1.5">
                  <span className="text-[10px] uppercase font-bold tracking-wider text-violet-400 flex items-center gap-1">
                    Matched Source Excerpt
                  </span>
                  <div className="p-3.5 rounded-xl bg-black/40 border border-white/10 text-slate-300 text-xs font-mono leading-relaxed max-h-56 overflow-y-auto scrollbar-thin whitespace-pre-wrap">
                    {activeCitation.snippet ||
                      activeCitation.text ||
                      activeCitation.excerpt ||
                      `Grounding context verified from document "${activeCitation.filename}". The answer was synthesized using these indexed chunk embeddings.`}
                  </div>
                </div>

                <div className="flex items-center justify-between pt-3 border-t border-white/10 text-[11px] text-slate-400">
                  <span>Grounding verification: Indexed Vector Embeddings</span>
                  <button
                    type="button"
                    onClick={() => setActiveCitation(null)}
                    className="px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 text-white font-medium text-xs shadow-md shadow-violet-600/25 transition-all cursor-pointer"
                  >
                    Close
                  </button>
                </div>
              </div>
            </m.div>
          </div>
        )}
      </AnimatePresence>
    </>
  );
};

export default ChatMessageList;
