import React from 'react';
import { m, AnimatePresence } from 'motion/react';
import {
  Settings,
  X,
  Sliders,
  Sparkles,
  Database,
  User,
  Info,
  BookOpen,
  Globe,
  Download,
  Trash2,
  ScanFace,
  ShieldCheck,
  ShieldAlert,
  Bot,
  AlertCircle,
  Loader2,
} from 'lucide-react';

export const ChatSettingsModal = ({
  settingsOpen,
  setSettingsOpen,
  shouldReduceMotion,
  settingsTab,
  setSettingsTab,
  manualReduceMotion,
  toggleManualReduceMotion,
  osReducedMotion,
  defaultRagEnabled,
  updateDefaultRag,
  defaultWebSearchEnabled,
  updateDefaultWeb,
  handleExportAllConversations,
  setClearChatsInput,
  setClearChatsModalOpen,
  user,
  clerkUser,
  loginMethod,
  navigate,
  setDeleteAccountInput,
  setDeleteAccountError,
  setDeleteAccountModalOpen,
  deleteAccountModalOpen,
  isDeletingAccount,
  deleteAccountInput,
  deleteAccountError,
  handleConfirmDeleteAccount,
  clearChatsModalOpen,
  isClearingChats,
  clearChatsInput,
  sessions,
  handleConfirmClearAllChats,
}) => {
  return (
    <>
      <AnimatePresence>
        {settingsOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4">
            <m.div
              initial={shouldReduceMotion ? { opacity: 1 } : { opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={shouldReduceMotion ? { opacity: 0 } : { opacity: 0 }}
              className="fixed inset-0 bg-black/70 backdrop-blur-md"
              onClick={() => setSettingsOpen(false)}
            />

            <m.div
              initial={shouldReduceMotion ? { opacity: 1 } : { opacity: 0, scale: 0.95, y: 15 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.95, y: 15 }}
              transition={{ duration: 0.2 }}
              className="relative z-10 w-full max-w-xl glass-panel border border-white/15 rounded-3xl overflow-hidden shadow-2xl bg-[#0d0b1d]/95 flex flex-col max-h-[85vh] text-left text-slate-200"
            >
              {/* Modal Header */}
              <div className="flex items-center justify-between px-6 py-4 border-b border-white/10 shrink-0">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-xl bg-violet-600/20 border border-violet-500/30 flex items-center justify-center text-violet-400">
                    <Settings className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-white">Settings</h3>
                    <p className="text-[11px] text-slate-400">Preferences, defaults, and data management</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setSettingsOpen(false)}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Modal Navigation Tabs */}
              <div className="flex items-center gap-1 px-4 pt-2 border-b border-white/10 overflow-x-auto shrink-0 bg-white/[0.01]">
                {[
                  { id: 'appearance', label: 'Appearance', icon: Sliders },
                  { id: 'defaults', label: 'Defaults', icon: Sparkles },
                  { id: 'data', label: 'Data', icon: Database },
                  { id: 'account', label: 'Account', icon: User },
                  { id: 'about', label: 'About', icon: Info },
                ].map((tab) => {
                  const Icon = tab.icon;
                  const isActive = settingsTab === tab.id;
                  return (
                    <button
                      key={tab.id}
                      type="button"
                      onClick={() => setSettingsTab(tab.id)}
                      className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition-all cursor-pointer whitespace-nowrap ${
                        isActive
                          ? 'border-violet-500 text-violet-300'
                          : 'border-transparent text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      <Icon className="w-3.5 h-3.5" />
                      <span>{tab.label}</span>
                    </button>
                  );
                })}
              </div>

              {/* Modal Body / Tab Content */}
              <div className="p-6 overflow-y-auto space-y-5 text-xs flex-1">
                {/* TAB 1: APPEARANCE */}
                {settingsTab === 'appearance' && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-4 rounded-2xl bg-white/[0.03] border border-white/10">
                      <div className="space-y-1 max-w-[80%]">
                        <p className="font-semibold text-slate-100 text-sm">Force Reduced Motion</p>
                        <p className="text-slate-400 text-[11px] leading-relaxed">
                          Disable all animated transitions and micro-interactions across the application.
                          Overrides operating system preferences.
                        </p>
                        <p className="text-[10px] text-slate-500">
                          OS reduced-motion preference:{' '}
                          <span className={osReducedMotion ? 'text-violet-400' : 'text-slate-400'}>
                            {osReducedMotion ? 'Detected (Active)' : 'Inactive'}
                          </span>
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={toggleManualReduceMotion}
                        className={`w-12 h-6 rounded-full transition-colors cursor-pointer relative p-0.5 border ${
                          manualReduceMotion
                            ? 'bg-violet-600 border-violet-500'
                            : 'bg-white/10 border-white/20'
                        }`}
                      >
                        <div
                          className={`w-5 h-5 rounded-full bg-white transition-transform ${
                            manualReduceMotion ? 'translate-x-6' : 'translate-x-0'
                          }`}
                        />
                      </button>
                    </div>
                  </div>
                )}

                {/* TAB 2: DEFAULTS */}
                {settingsTab === 'defaults' && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-4 rounded-2xl bg-white/[0.03] border border-white/10">
                      <div className="space-y-1 max-w-[80%]">
                        <p className="font-semibold text-slate-100 text-sm flex items-center gap-1.5">
                          <BookOpen className="w-3.5 h-3.5 text-violet-400" />
                          <span>Default RAG Retrieval</span>
                        </p>
                        <p className="text-slate-400 text-[11px] leading-relaxed">
                          Automatically enable document vector search on new conversations. When active, queries
                          retrieve grounded answers from indexed knowledge files.
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => updateDefaultRag(!defaultRagEnabled)}
                        className={`w-12 h-6 rounded-full transition-colors cursor-pointer relative p-0.5 border ${
                          defaultRagEnabled
                            ? 'bg-violet-600 border-violet-500'
                            : 'bg-white/10 border-white/20'
                        }`}
                      >
                        <div
                          className={`w-5 h-5 rounded-full bg-white transition-transform ${
                            defaultRagEnabled ? 'translate-x-6' : 'translate-x-0'
                          }`}
                        />
                      </button>
                    </div>

                    <div className="flex items-center justify-between p-4 rounded-2xl bg-white/[0.03] border border-white/10">
                      <div className="space-y-1 max-w-[80%]">
                        <p className="font-semibold text-slate-100 text-sm flex items-center gap-1.5">
                          <Globe className="w-3.5 h-3.5 text-fuchsia-400" />
                          <span>Default Web Search</span>
                        </p>
                        <p className="text-slate-400 text-[11px] leading-relaxed">
                          Automatically enable real-time internet search on new conversations via Groq Compound.
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => updateDefaultWeb(!defaultWebSearchEnabled)}
                        className={`w-12 h-6 rounded-full transition-colors cursor-pointer relative p-0.5 border ${
                          defaultWebSearchEnabled
                            ? 'bg-fuchsia-600 border-fuchsia-500'
                            : 'bg-white/10 border-white/20'
                        }`}
                      >
                        <div
                          className={`w-5 h-5 rounded-full bg-white transition-transform ${
                            defaultWebSearchEnabled ? 'translate-x-6' : 'translate-x-0'
                          }`}
                        />
                      </button>
                    </div>
                  </div>
                )}

                {/* TAB 3: DATA */}
                {settingsTab === 'data' && (
                  <div className="space-y-4">
                    <div className="p-4 rounded-2xl bg-white/[0.03] border border-white/10 flex items-center justify-between gap-3">
                      <div className="space-y-1">
                        <p className="font-semibold text-slate-100 text-sm">Export All Conversations</p>
                        <p className="text-slate-400 text-[11px]">
                          Download a complete JSON export of all your chat sessions and transcripts.
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={handleExportAllConversations}
                        className="px-3 py-2 rounded-xl bg-violet-600 hover:bg-violet-500 text-white font-medium text-xs shadow-md shadow-violet-600/25 transition-all cursor-pointer whitespace-nowrap flex items-center gap-1.5"
                      >
                        <Download className="w-3.5 h-3.5" />
                        <span>Export All</span>
                      </button>
                    </div>

                    <div className="p-4 rounded-2xl bg-rose-500/5 border border-rose-500/25 flex items-center justify-between gap-3">
                      <div className="space-y-1">
                        <p className="font-semibold text-rose-300 text-sm">Clear All Chats</p>
                        <p className="text-slate-400 text-[11px]">
                          Permanently delete all conversations. Requires typed confirmation.
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => {
                          setClearChatsInput('');
                          setClearChatsModalOpen(true);
                        }}
                        className="px-3 py-2 rounded-xl bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 hover:text-white border border-rose-500/30 font-medium text-xs transition-all cursor-pointer whitespace-nowrap flex items-center gap-1.5"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        <span>Clear All</span>
                      </button>
                    </div>
                  </div>
                )}

                {/* TAB 4: ACCOUNT */}
                {settingsTab === 'account' && (
                  <div className="space-y-4">
                    <div className="p-4 rounded-2xl bg-white/[0.03] border border-white/10 space-y-3">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-indigo-600 to-violet-600 flex items-center justify-center text-white font-bold text-sm shadow-md">
                          {user ? user.charAt(0).toUpperCase() : 'U'}
                        </div>
                        <div>
                          <p className="font-semibold text-white text-sm">{user}</p>
                          <p className="text-[11px] text-slate-400">
                            {clerkUser?.primaryEmailAddress?.emailAddress || 'User Account'}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 pt-2 border-t border-white/10 text-[11px] text-slate-400">
                        <span className="font-medium text-slate-300">Auth Method:</span>
                        {loginMethod === 'face' ? (
                          <span className="inline-flex items-center gap-1 text-emerald-400 font-medium">
                            <ScanFace className="w-3.5 h-3.5" /> Face Recognition Verified
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-indigo-300 font-medium">
                            <ShieldCheck className="w-3.5 h-3.5" /> Password Authentication
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="p-4 rounded-2xl bg-white/[0.03] border border-white/10 flex items-center justify-between">
                      <div className="space-y-0.5">
                        <p className="font-semibold text-slate-100 text-sm">Biometric Face Authentication</p>
                        <p className="text-[11px] text-slate-400">Register, manage, or update your facial recognition encodings.</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => {
                          setSettingsOpen(false);
                          navigate('/account/add-face');
                        }}
                        className="px-3 py-1.5 rounded-xl bg-indigo-600/20 hover:bg-indigo-600/40 text-indigo-300 border border-indigo-500/30 text-xs font-medium transition-all cursor-pointer"
                      >
                        Manage Faces
                      </button>
                    </div>

                    <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30 space-y-2.5">
                      <div className="flex items-start gap-2 text-rose-300">
                        <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5 text-rose-400" />
                        <div className="space-y-0.5">
                          <p className="font-semibold text-rose-200 text-sm">Danger Zone: Delete Account</p>
                          <p className="text-[11px] text-rose-300/80 leading-relaxed">
                            Permanently delete your account, enrolled biometric faces, uploaded documents,
                            and all chat conversations. This action cannot be reversed.
                          </p>
                        </div>
                      </div>
                      <div className="pt-2 flex justify-end">
                        <button
                          type="button"
                          onClick={() => {
                            setDeleteAccountInput('');
                            setDeleteAccountError('');
                            setDeleteAccountModalOpen(true);
                          }}
                          className="px-3.5 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-medium text-xs shadow-md shadow-rose-600/25 transition-all cursor-pointer flex items-center gap-1.5"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                          <span>Delete Account</span>
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {/* TAB 5: ABOUT */}
                {settingsTab === 'about' && (
                  <div className="space-y-4">
                    <div className="p-5 rounded-2xl bg-white/[0.03] border border-white/10 space-y-3">
                      <div className="flex items-center gap-2.5">
                        <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-violet-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-violet-600/30">
                          <Bot className="w-5 h-5" />
                        </div>
                        <div>
                          <h4 className="font-bold text-white text-sm flex items-center gap-2">
                            <span>OmniRAG AI</span>
                            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-violet-500/20 text-violet-300 border border-violet-500/30">
                              v4.0.0
                            </span>
                          </h4>
                          <p className="text-[11px] text-slate-400">Contextual Knowledge Chat &amp; Search Engine</p>
                        </div>
                      </div>
                      <p className="text-slate-300 text-xs leading-relaxed">
                        OmniRAG AI is a production-grade conversational intelligence platform featuring
                        vectorized document retrieval (RAG), real-time autonomous web search via Groq Compound,
                        high-speed Groq LLM inference, and biometric face authentication.
                      </p>
                      <div className="grid grid-cols-2 gap-2 pt-2 border-t border-white/10 text-[11px] text-slate-400">
                        <div>
                          <span className="text-slate-500">Engine:</span> Grounded RAG + Compound
                        </div>
                        <div>
                          <span className="text-slate-500">LLM Tier:</span> Groq API
                        </div>
                        <div>
                          <span className="text-slate-500">Biometrics:</span> Multi-Face Encodings
                        </div>
                        <div>
                          <span className="text-slate-500">Embeddings:</span> HuggingFace Vectorizer
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Modal Footer */}
              <div className="px-6 py-3.5 border-t border-white/10 flex justify-end shrink-0 bg-white/[0.01]">
                <button
                  type="button"
                  onClick={() => setSettingsOpen(false)}
                  className="px-4 py-1.5 rounded-xl bg-white/10 hover:bg-white/15 text-slate-200 text-xs font-medium transition-colors cursor-pointer"
                >
                  Done
                </button>
              </div>
            </m.div>
          </div>
        )}
      </AnimatePresence>

      {/* Restored Account Deletion Confirmation Modal */}
      <AnimatePresence>
        {deleteAccountModalOpen && (
          <div className="fixed inset-0 z-60 flex items-center justify-center p-4">
            <m.div
              initial={shouldReduceMotion ? { opacity: 1 } : { opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={shouldReduceMotion ? { opacity: 0 } : { opacity: 0 }}
              className="fixed inset-0 bg-black/80 backdrop-blur-md"
              onClick={() => !isDeletingAccount && setDeleteAccountModalOpen(false)}
            />

            <m.div
              initial={shouldReduceMotion ? { opacity: 1 } : { opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.95 }}
              className="relative z-10 w-full max-w-md glass-panel border border-rose-500/40 rounded-3xl p-6 shadow-2xl bg-[#140b12]/95 text-left text-slate-200 space-y-4"
            >
              <div className="flex items-center gap-3 text-rose-400">
                <div className="w-10 h-10 rounded-xl bg-rose-500/20 border border-rose-500/40 flex items-center justify-center shrink-0">
                  <ShieldAlert className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">Delete OmniRAG Account</h3>
                  <p className="text-[11px] text-rose-300/80">Permanent and irreversible</p>
                </div>
              </div>

              <p className="text-xs text-slate-300 leading-relaxed">
                This will permanently delete your account, face encodings, indexed documents, and all chat history.
                To confirm, type <span className="font-mono font-bold text-rose-300">DELETE</span> below:
              </p>

              <input
                type="text"
                value={deleteAccountInput}
                onChange={(e) => setDeleteAccountInput(e.target.value)}
                placeholder="Type DELETE to confirm"
                disabled={isDeletingAccount}
                className="w-full px-3.5 py-2.5 rounded-xl bg-black/40 border border-rose-500/40 focus:border-rose-400 focus:outline-none text-xs font-mono text-white placeholder-slate-500"
              />

              {deleteAccountError && (
                <p className="text-xs text-rose-400 flex items-center gap-1">
                  <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                  <span>{deleteAccountError}</span>
                </p>
              )}

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  disabled={isDeletingAccount}
                  onClick={() => setDeleteAccountModalOpen(false)}
                  className="px-3.5 py-2 rounded-xl bg-white/10 hover:bg-white/15 text-slate-300 text-xs font-medium transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={deleteAccountInput.trim() !== 'DELETE' || isDeletingAccount}
                  onClick={handleConfirmDeleteAccount}
                  className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-semibold shadow-md shadow-rose-600/30 transition-all cursor-pointer flex items-center gap-1.5"
                >
                  {isDeletingAccount && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>{isDeletingAccount ? 'Deleting...' : 'Delete Forever'}</span>
                </button>
              </div>
            </m.div>
          </div>
        )}
      </AnimatePresence>

      {/* Clear All Chats Confirmation Modal */}
      <AnimatePresence>
        {clearChatsModalOpen && (
          <div className="fixed inset-0 z-60 flex items-center justify-center p-4">
            <m.div
              initial={shouldReduceMotion ? { opacity: 1 } : { opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={shouldReduceMotion ? { opacity: 0 } : { opacity: 0 }}
              className="fixed inset-0 bg-black/80 backdrop-blur-md"
              onClick={() => !isClearingChats && setClearChatsModalOpen(false)}
            />

            <m.div
              initial={shouldReduceMotion ? { opacity: 1 } : { opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.95 }}
              className="relative z-10 w-full max-w-md glass-panel border border-rose-500/40 rounded-3xl p-6 shadow-2xl bg-[#140b12]/95 text-left text-slate-200 space-y-4"
            >
              <div className="flex items-center gap-3 text-rose-400">
                <div className="w-10 h-10 rounded-xl bg-rose-500/20 border border-rose-500/40 flex items-center justify-center shrink-0">
                  <Trash2 className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">Clear All Conversations</h3>
                  <p className="text-[11px] text-rose-300/80">All session transcripts will be deleted</p>
                </div>
              </div>

              <p className="text-xs text-slate-300 leading-relaxed">
                This will delete all {sessions.length} chat session{sessions.length === 1 ? '' : 's'}.
                To confirm, type <span className="font-mono font-bold text-rose-300">CLEAR</span> below:
              </p>

              <input
                type="text"
                value={clearChatsInput}
                onChange={(e) => setClearChatsInput(e.target.value)}
                placeholder="Type CLEAR to confirm"
                disabled={isClearingChats}
                className="w-full px-3.5 py-2.5 rounded-xl bg-black/40 border border-rose-500/40 focus:border-rose-400 focus:outline-none text-xs font-mono text-white placeholder-slate-500"
              />

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  disabled={isClearingChats}
                  onClick={() => setClearChatsModalOpen(false)}
                  className="px-3.5 py-2 rounded-xl bg-white/10 hover:bg-white/15 text-slate-300 text-xs font-medium transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={
                    (clearChatsInput.trim().toUpperCase() !== 'CLEAR' &&
                      clearChatsInput.trim().toUpperCase() !== 'DELETE') ||
                    isClearingChats
                  }
                  onClick={handleConfirmClearAllChats}
                  className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-semibold shadow-md shadow-rose-600/30 transition-all cursor-pointer flex items-center gap-1.5"
                >
                  {isClearingChats && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>{isClearingChats ? 'Clearing...' : 'Clear All Chats'}</span>
                </button>
              </div>
            </m.div>
          </div>
        )}
      </AnimatePresence>
    </>
  );
};

export default ChatSettingsModal;
