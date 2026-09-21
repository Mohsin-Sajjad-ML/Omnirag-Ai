import React from 'react';
import { m, AnimatePresence } from 'motion/react';
import {
  Layers,
  ChevronDown,
  Search,
  SearchX,
  X,
  FileText,
  Paperclip,
  BookOpen,
  Globe,
  Mic,
  Send,
  Loader2,
  Trash2,
} from 'lucide-react';

export const ChatInputBar = ({
  docSelectorRef,
  shouldReduceMotion,
  docSelectorOpen,
  setDocSelectorOpen,
  setShowUploadMenu,
  selectedDocIds,
  documents,
  handleSelectAllDocs,
  docSearchQuery,
  setDocSearchQuery,
  filteredScopeDocuments,
  toggleDocSelection,
  handleSendMessage,
  fileInputRef,
  handleFileSelect,
  inputQuery,
  setInputQuery,
  isSending,
  uploadMenuRef,
  showUploadMenu,
  uploadMenuItems,
  ragEnabled,
  setRagEnabled,
  webSearchEnabled,
  setWebSearchEnabled,
  isRecording,
  cancelVoiceRecording,
  isTranscribing,
  toggleVoiceRecording,
  analyserRef,
  audioLevels,
  isUndoDeleting,
  undoSessionData,
  handleUndoDelete,
}) => {
  return (
    <>
      <div className="px-4 sm:px-6 md:px-8 pb-4 sm:pb-6 pt-1 bg-transparent shrink-0">
        {/* Sculpted Glass Input Card */}
        <form
          onSubmit={handleSendMessage}
          className="w-full max-w-4xl mx-auto rounded-[24px] sm:rounded-[28px] bg-[#141226]/85 hover:bg-[#16142a]/90 focus-within:bg-[#16142a]/95 border border-white/[0.14] focus-within:border-violet-500/60 shadow-[0_16px_45px_rgba(0,0,0,0.55)] focus-within:shadow-[0_0_35px_rgba(139,92,246,0.22)] backdrop-blur-2xl transition-all p-3 sm:p-3.5 flex flex-col gap-2.5 relative"
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileSelect}
            accept=".pdf,.docx,.txt,.csv"
            className="hidden"
          />

          <div className="w-full px-1">
            <textarea
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  if (inputQuery.trim() && !isSending) {
                    handleSendMessage(e);
                  }
                }
              }}
              rows={1}
              placeholder={
                documents.length === 0
                  ? 'Send a message or drop a file...'
                  : `Ask OmniRAG about your ${documents.length} document${documents.length === 1 ? '' : 's'}...`
              }
              disabled={isSending}
              className="w-full bg-transparent text-xs sm:text-sm text-slate-100 placeholder-slate-400 focus:outline-none resize-none min-h-[36px] max-h-[140px] py-1 leading-relaxed"
            />
          </div>

          <div className="flex items-center justify-between gap-2 pt-1.5 border-t border-white/[0.06]">
            <div className="flex items-center gap-1.5 flex-wrap">
              <div className="relative" ref={uploadMenuRef}>
                <m.button
                  type="button"
                  whileHover={shouldReduceMotion ? {} : { scale: 1.03 }}
                  whileTap={shouldReduceMotion ? {} : { scale: 0.97 }}
                  onClick={() => {
                    setShowUploadMenu((prev) => !prev);
                    setDocSelectorOpen(false);
                  }}
                  title="Upload or attach documents"
                  className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/[0.06] hover:bg-white/[0.12] text-slate-300 hover:text-white border border-white/10 hover:border-violet-500/40 text-[11px] font-medium transition-all shadow-xs cursor-pointer"
                >
                  <Paperclip className="w-3 h-3 text-violet-400" />
                  <span>Files</span>
                </m.button>

                <AnimatePresence>
                  {showUploadMenu && (
                    <m.div
                      initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.95, y: 10 }}
                      animate={{ opacity: 1, scale: 1, y: 0 }}
                      exit={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.95, y: 10 }}
                      transition={{ duration: 0.18 }}
                      className="absolute bottom-full left-0 mb-3 w-56 glass-panel border border-white/15 rounded-xl shadow-2xl shadow-black/80 overflow-hidden z-50 backdrop-blur-xl"
                    >
                      <ul className="p-1.5 space-y-1">
                        {uploadMenuItems.map((item) => {
                          const Icon = item.icon;
                          return (
                            <li key={item.id}>
                              <m.button
                                type="button"
                                whileHover={shouldReduceMotion ? {} : { scale: 1.02, x: 2 }}
                                whileTap={shouldReduceMotion ? {} : { scale: 0.97 }}
                                transition={{ duration: 0.15 }}
                                onClick={() => {
                                  setShowUploadMenu(false);
                                  item.action();
                                }}
                                className="group w-full flex items-center gap-3 px-3 py-2 text-xs font-medium text-slate-200 hover:text-white hover:bg-gradient-to-r hover:from-violet-600 hover:to-fuchsia-600 rounded-lg transition-colors text-left cursor-pointer"
                              >
                                <Icon className="w-4 h-4 text-violet-400 group-hover:text-white transition-colors" />
                                <span>{item.label}</span>
                              </m.button>
                            </li>
                          );
                        })}
                      </ul>
                    </m.div>
                  )}
                </AnimatePresence>
              </div>

              {/* Inline Document Scope Selector Pill & Dropdown */}
              <div className="relative inline-block" ref={docSelectorRef}>
                <m.button
                  type="button"
                  whileHover={shouldReduceMotion ? {} : { scale: 1.03 }}
                  whileTap={shouldReduceMotion ? {} : { scale: 0.97 }}
                  onClick={() => {
                    setDocSelectorOpen((prev) => !prev);
                    setShowUploadMenu(false);
                  }}
                  title="Select document retrieval scope"
                  className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-medium transition-all shadow-xs cursor-pointer border ${
                    selectedDocIds.length === 0
                      ? 'bg-white/[0.06] hover:bg-white/[0.12] text-slate-300 hover:text-white border-white/10'
                      : 'bg-violet-600/20 text-violet-300 border-violet-500/40'
                  }`}
                >
                  <Layers className="w-3 h-3 text-cyan-400" />
                  <span>
                    {selectedDocIds.length === 0
                      ? `Docs (${documents.length})`
                      : `${selectedDocIds.length} Selected`}
                  </span>
                  <ChevronDown className={`w-2.5 h-2.5 text-slate-400 transition-transform ${docSelectorOpen ? 'rotate-180' : ''}`} />
                </m.button>

                {/* Document Selector Dropdown Menu */}
                {docSelectorOpen && (
                  <div className="absolute bottom-full mb-3 left-0 z-50 w-72 sm:w-84 glass-panel border border-white/15 rounded-2xl shadow-2xl p-2.5 backdrop-blur-2xl flex flex-col bg-[#120f24]/95 border-violet-500/20">
                    <div className="flex items-center justify-between pb-2 mb-2 border-b border-white/10">
                      <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                        Query Retrieval Scope
                      </span>
                      <button
                        type="button"
                        onClick={handleSelectAllDocs}
                        className="text-[11px] text-violet-400 hover:text-violet-300 font-medium cursor-pointer transition-colors"
                      >
                        {selectedDocIds.length === 0 ? 'Select Specific' : 'Query All'}
                      </button>
                    </div>

                    {documents.length > 0 && (
                      <div className="relative mb-2">
                        <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
                        <input
                          type="text"
                          value={docSearchQuery}
                          onChange={(e) => setDocSearchQuery(e.target.value)}
                          placeholder="Search documents..."
                          className="w-full pl-8 pr-7 py-1.5 rounded-lg bg-black/40 border border-white/10 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-violet-500/50 transition-colors"
                        />
                        {docSearchQuery && (
                          <button
                            type="button"
                            onClick={() => setDocSearchQuery('')}
                            className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 p-0.5 rounded cursor-pointer"
                          >
                            <X className="w-3 h-3" />
                          </button>
                        )}
                      </div>
                    )}

                    {documents.length === 0 ? (
                      <div className="p-3 text-center text-xs text-slate-500">
                        No indexed documents found. Upload a file using the + button.
                      </div>
                    ) : filteredScopeDocuments.length === 0 ? (
                      <div className="p-3 text-center text-xs text-slate-400 flex flex-col items-center gap-1">
                        <SearchX className="w-4 h-4 text-slate-500" />
                        <span>No documents match &quot;{docSearchQuery}&quot;</span>
                      </div>
                    ) : (
                      <div className="max-h-52 overflow-y-auto scrollbar-thin scrollbar-thumb-slate-700 pr-0.5 space-y-1">
                        {!docSearchQuery.trim() && (
                          <>
                            <label className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-white/5 cursor-pointer text-xs text-slate-200 transition-colors">
                              <input
                                type="checkbox"
                                checked={selectedDocIds.length === 0}
                                onChange={handleSelectAllDocs}
                                className="rounded border-slate-700 text-violet-600 focus:ring-0 focus:ring-offset-0 bg-slate-800 cursor-pointer"
                              />
                              <span className="font-semibold text-slate-100">All Documents</span>
                              <span className="ml-auto text-[10px] text-slate-500">({documents.length})</span>
                            </label>
                            <div className="border-t border-white/10 my-1" />
                          </>
                        )}

                        {filteredScopeDocuments.map((doc) => {
                          const isSelected = selectedDocIds.includes(doc.id);
                          return (
                            <label
                              key={doc.id}
                              className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-white/5 cursor-pointer text-xs text-slate-300 transition-colors"
                            >
                              <input
                                type="checkbox"
                                checked={isSelected}
                                onChange={() => toggleDocSelection(doc.id)}
                                className="rounded border-slate-700 text-violet-600 focus:ring-0 focus:ring-offset-0 bg-slate-800 cursor-pointer"
                              />
                              <FileText className="w-3.5 h-3.5 text-violet-400 shrink-0" />
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

              <m.button
                type="button"
                onClick={() => setRagEnabled((prev) => !prev)}
                whileHover={shouldReduceMotion ? {} : { scale: 1.03 }}
                whileTap={shouldReduceMotion ? {} : { scale: 0.97 }}
                transition={{ duration: 0.2 }}
                title={ragEnabled ? 'RAG Mode Active: Grounded retrieval from your documents' : 'RAG Mode Disabled'}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-medium transition-all duration-200 cursor-pointer border select-none ${
                  ragEnabled
                    ? 'bg-violet-600/30 text-violet-200 border-violet-500/80 shadow-[0_0_12px_rgba(139,92,246,0.35)] ring-1 ring-violet-400/40'
                    : 'bg-white/[0.04] hover:bg-white/[0.08] text-slate-400 hover:text-slate-200 border-white/10'
                }`}
              >
                <BookOpen className={`w-3 h-3 transition-colors duration-200 ${ragEnabled ? 'text-violet-300' : 'text-slate-400'}`} />
                <span>RAG</span>
                <span
                  className={`w-1.5 h-1.5 rounded-full transition-all duration-200 ${
                    ragEnabled
                      ? 'bg-violet-400 shadow-[0_0_6px_rgba(167,139,250,0.9)] animate-pulse'
                      : 'bg-slate-600'
                  }`}
                />
              </m.button>

              <m.button
                type="button"
                onClick={() => setWebSearchEnabled((prev) => !prev)}
                whileHover={shouldReduceMotion ? {} : { scale: 1.03 }}
                whileTap={shouldReduceMotion ? {} : { scale: 0.97 }}
                transition={{ duration: 0.2 }}
                title={webSearchEnabled ? 'Real-Time Web Search Active: uses groq/compound' : 'Web Search Disabled'}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-medium transition-all duration-200 cursor-pointer border select-none ${
                  webSearchEnabled
                    ? 'bg-fuchsia-600/30 text-fuchsia-200 border-fuchsia-500/80 shadow-[0_0_12px_rgba(217,70,239,0.35)] ring-1 ring-fuchsia-400/40'
                    : 'bg-white/[0.04] hover:bg-white/[0.08] text-slate-400 hover:text-slate-200 border-white/10'
                }`}
              >
                <Globe className={`w-3 h-3 transition-colors duration-200 ${webSearchEnabled ? 'text-fuchsia-300' : 'text-slate-400'}`} />
                <span>Web Search</span>
                <span
                  className={`w-1.5 h-1.5 rounded-full transition-all duration-200 ${
                    webSearchEnabled
                      ? 'bg-fuchsia-400 shadow-[0_0_6px_rgba(244,114,182,0.9)] animate-pulse'
                      : 'bg-slate-600'
                  }`}
                />
              </m.button>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              {isRecording && (
                <m.button
                  type="button"
                  whileHover={shouldReduceMotion ? {} : { scale: 1.05 }}
                  whileTap={shouldReduceMotion ? {} : { scale: 0.95 }}
                  transition={{ duration: 0.15 }}
                  onClick={cancelVoiceRecording}
                  title="Cancel voice recording"
                  className="p-1.5 rounded-full bg-rose-950/50 hover:bg-rose-900/70 text-rose-300 hover:text-rose-100 border border-rose-500/40 shadow-sm flex items-center justify-center transition-colors cursor-pointer"
                >
                  <X className="w-3.5 h-3.5" />
                </m.button>
              )}

              <m.button
                type="button"
                whileHover={shouldReduceMotion || isTranscribing ? {} : { scale: 1.05 }}
                whileTap={shouldReduceMotion || isTranscribing ? {} : { scale: 0.95 }}
                transition={{ duration: 0.15 }}
                onClick={toggleVoiceRecording}
                disabled={isTranscribing}
                title={isRecording ? 'Stop and transcribe voice' : isTranscribing ? 'Transcribing audio...' : 'Dictate with voice'}
                className={`p-2 rounded-full transition-all shadow-sm flex items-center justify-center cursor-pointer ${
                  isRecording
                    ? 'bg-gradient-to-r from-rose-600 to-pink-600 text-white shadow-lg shadow-rose-600/30 ring-2 ring-rose-400/60 px-2.5'
                    : isTranscribing
                    ? 'bg-violet-950/60 text-violet-300 border border-violet-500/40 cursor-wait'
                    : 'bg-white/[0.06] hover:bg-white/[0.14] text-violet-300 hover:text-white border border-white/10 hover:border-violet-500/40 shadow-xs'
                }`}
              >
                {isRecording ? (
                  <div className="flex items-center gap-0.5 h-3.5 px-0.5" aria-label="Recording audio">
                    {[0, 1, 2, 3, 4].map((i) => (
                      <m.span
                        key={i}
                        className="w-1 bg-white rounded-full inline-block"
                        animate={
                          shouldReduceMotion
                            ? { height: 8 }
                            : analyserRef.current
                            ? { height: audioLevels[i] || 6 }
                            : {
                                height: [
                                  [4, 14, 6, 16, 4],
                                  [6, 18, 10, 20, 6],
                                  [8, 22, 14, 22, 8],
                                  [6, 18, 10, 20, 6],
                                  [4, 14, 6, 16, 4],
                                ][i],
                              }
                        }
                        transition={
                          shouldReduceMotion
                            ? { duration: 0 }
                            : analyserRef.current
                            ? { type: 'spring', stiffness: 450, damping: 20 }
                            : {
                                repeat: Infinity,
                                repeatType: 'reverse',
                                duration: 0.45 + i * 0.1,
                                ease: 'easeInOut',
                              }
                        }
                        style={{ minHeight: '3px' }}
                      />
                    ))}
                  </div>
                ) : isTranscribing ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-violet-400" />
                ) : (
                  <Mic className="w-3.5 h-3.5" />
                )}
              </m.button>

              <m.button
                type="submit"
                whileHover={shouldReduceMotion || !inputQuery.trim() || isSending ? {} : { scale: 1.08 }}
                whileTap={shouldReduceMotion || !inputQuery.trim() || isSending ? {} : { scale: 0.92 }}
                transition={{ duration: 0.15 }}
                disabled={!inputQuery.trim() || isSending}
                title="Send query"
                className="w-8 h-8 rounded-full bg-gradient-to-tr from-violet-600 via-violet-500 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 disabled:from-slate-800 disabled:to-slate-800 disabled:text-slate-600 text-white flex items-center justify-center shadow-lg shadow-violet-600/35 transition-all cursor-pointer disabled:cursor-not-allowed"
              >
                <Send className="w-3.5 h-3.5 ml-0.5" />
              </m.button>
            </div>
          </div>
        </form>
      </div>

      {/* Delete Undo Toast */}
      <AnimatePresence>
        {isUndoDeleting && undoSessionData && (
          <m.div
            initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: 50, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: 20, scale: 0.9 }}
            transition={{ duration: 0.2 }}
            className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[100] flex items-center gap-4 glass-panel bg-slate-900/95 border border-white/20 px-4 py-3 rounded-2xl shadow-2xl overflow-hidden backdrop-blur-xl"
          >
            <div className="text-xs sm:text-sm font-medium text-slate-100 flex items-center gap-2">
              <Trash2 className="w-3.5 h-3.5 text-rose-400 shrink-0" />
              <span className="truncate max-w-[200px]">
                {undoSessionData.session?.title ? `"${undoSessionData.session.title}" deleted` : 'Chat deleted'}
              </span>
            </div>
            <button
              type="button"
              onClick={handleUndoDelete}
              className="bg-violet-600 hover:bg-violet-500 text-white text-xs font-semibold px-3.5 py-1.5 rounded-xl shadow-md transition-all active:scale-95 cursor-pointer shrink-0"
            >
              Undo
            </button>
            <m.div
              initial={{ width: "100%" }}
              animate={{ width: "0%" }}
              transition={{ duration: 5, ease: "linear" }}
              className="absolute bottom-0 left-0 h-1 bg-gradient-to-r from-violet-500 via-fuchsia-500 to-indigo-500"
            />
          </m.div>
        )}
      </AnimatePresence>
    </>
  );
};

export default ChatInputBar;
