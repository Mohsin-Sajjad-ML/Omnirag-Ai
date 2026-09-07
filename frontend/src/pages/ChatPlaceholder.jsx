import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { LogOut, User, Bot, Camera, Sparkles, MessageSquare, Send } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { UploadDocument } from '../components/UploadDocument';
import { DocumentList } from '../components/DocumentList';

export const ChatPlaceholder = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  // State trigger to auto-refresh DocumentList upon successful upload
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const handleUploadSuccess = () => {
    setRefreshTrigger((prev) => prev + 1);
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-900 text-slate-100">
      {/* Header Bar */}
      <header className="sticky top-0 z-40 border-b border-slate-800 bg-slate-900/80 backdrop-blur-md px-6 py-3.5 flex items-center justify-between shadow-sm">
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-md shadow-indigo-600/30">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <h1 className="font-bold text-slate-100 text-sm sm:text-base">OmniRAG AI Chat</h1>
            <p className="text-[11px] text-indigo-400 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block animate-pulse"></span>
              Authenticated & Secure
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={() => navigate('/account/add-face')}
            className="flex items-center space-x-1.5 text-xs text-indigo-300 hover:text-white bg-indigo-600/20 hover:bg-indigo-600/40 px-3 py-1.5 rounded-lg border border-indigo-500/30 transition-all"
            title="Register or update your biometric face login"
          >
            <Camera className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Biometrics</span>
          </button>
          <div className="flex items-center space-x-2 bg-slate-800 px-3 py-1.5 rounded-full border border-slate-700 text-xs">
            <User className="w-3.5 h-3.5 text-indigo-400" />
            <span className="font-medium text-slate-200">{user}</span>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center space-x-1.5 text-xs text-slate-400 hover:text-rose-400 bg-slate-800/60 hover:bg-rose-500/10 px-3 py-1.5 rounded-lg border border-slate-700 hover:border-rose-500/30 transition-all"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Logout</span>
          </button>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-5xl w-full mx-auto p-4 sm:p-6 lg:p-8 space-y-6">
        {/* Welcome Section */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2">
          <div>
            <div className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 mb-1.5">
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              Document Pipeline (Prompt 4 of 12)
            </div>
            <h2 className="text-xl font-bold text-white tracking-tight">
              Knowledge Base Management
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Upload and manage your documents. Files are validated, parsed into plain text, and stored tied to your account.
            </p>
          </div>
        </div>

        {/* 1. Document Upload Component */}
        <UploadDocument onUploadSuccess={handleUploadSuccess} />

        {/* 2. Document List Component */}
        <DocumentList refreshTrigger={refreshTrigger} />

        {/* 3. Future Chat Interface Area (Stacked below documents, ready for Prompt 5+) */}
        <div className="w-full bg-slate-800/40 backdrop-blur-xl border border-dashed border-slate-700/60 rounded-2xl p-8 text-center space-y-4">
          <div className="w-14 h-14 bg-indigo-500/10 border border-indigo-500/20 rounded-2xl flex items-center justify-center text-indigo-400 mx-auto">
            <MessageSquare className="w-7 h-7" />
          </div>

          <div className="max-w-md mx-auto">
            <h3 className="text-base font-semibold text-white">RAG Chat Interface — Prompt 5</h3>
            <p className="text-xs text-slate-400 mt-1 leading-relaxed">
              In the next prompt, your parsed documents above will undergo chunking, embedding generation, and ChromaDB vector indexing to power real-time AI retrieval and conversational question-answering.
            </p>
          </div>

          {/* Disabled mock input mimicking where the chat prompt box will sit */}
          <div className="max-w-xl mx-auto pt-2">
            <div className="flex items-center gap-2 bg-slate-900/60 border border-slate-700/60 rounded-xl px-4 py-3 opacity-60 pointer-events-none">
              <input
                type="text"
                disabled
                placeholder="Ask questions about your uploaded documents (Available in Prompt 5)..."
                className="bg-transparent text-xs text-slate-400 w-full focus:outline-none placeholder-slate-500"
              />
              <div className="p-1.5 rounded-lg bg-indigo-600/30 text-indigo-400">
                <Send className="w-3.5 h-3.5" />
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};
