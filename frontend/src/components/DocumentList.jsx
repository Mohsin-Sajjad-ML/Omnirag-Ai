import React, { useEffect, useState } from 'react';
import {
  FileText,
  Trash2,
  AlertCircle,
  CheckCircle2,
  RefreshCw,
  Loader2,
  Clock,
  FileSpreadsheet,
  FileCode,
  File,
  Sparkles,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

/**
 * DocumentList Component
 *
 * Fetches and displays a user's uploaded documents via GET /documents/{username}.
 * Provides visual distinction for "parsed" vs "failed" documents.
 * Allows deleting documents via DELETE /documents/{document_id}?username={user}.
 */
export const DocumentList = ({ refreshTrigger, onDocumentDeleted }) => {
  const { user } = useAuth();

  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [deletingId, setDeletingId] = useState(null);

  const fetchDocuments = async (isSilent = false) => {
    if (!user) return;
    if (!isSilent) {
      setLoading(true);
      setError('');
    }

    try {
      const response = await api.get('/documents');
      setDocuments(response.data || []);
    } catch (err) {
      console.error('Failed to load documents:', err);
      if (!isSilent) {
        setError(
          err.response?.data?.detail ||
            err.response?.data?.message ||
            'Failed to load documents list from server.'
        );
      }
    } finally {
      if (!isSilent) {
        setLoading(false);
      }
    }
  };

  // Helper to determine if an indexed document is still awaiting its AI summary (within 90s of upload)
  const isRecentIndexedWithoutSummary = (doc) => {
    if (doc.status !== 'indexed' || doc.summary) return false;
    try {
      const docTime = new Date(doc.upload_timestamp).getTime();
      const now = Date.now();
      return (now - docTime) < 90000;
    } catch {
      return false;
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, [user, refreshTrigger]);

  // Prompt 8: Auto-poll if any newly uploaded document is indexed but waiting on its summary
  useEffect(() => {
    const hasPendingSummary = documents.some(isRecentIndexedWithoutSummary);
    if (!hasPendingSummary) return;

    const timer = setTimeout(() => {
      fetchDocuments(true);
    }, 3000);

    return () => clearTimeout(timer);
  }, [documents, user]);

  const handleDelete = async (docId, filename) => {
    const confirmed = window.confirm(`Are you sure you want to delete "${filename}"?`);
    if (!confirmed) return;

    setDeletingId(docId);
    try {
      await api.delete(`/documents/${docId}`);
      // Remove deleted document from state immediately
      setDocuments((prev) => prev.filter((d) => d.id !== docId));
      if (onDocumentDeleted) {
        onDocumentDeleted(docId);
      }
    } catch (err) {
      console.error('Delete error:', err);
      alert(
        err.response?.data?.detail ||
          err.response?.data?.message ||
          'Failed to delete document.'
      );
    } finally {
      setDeletingId(null);
    }
  };

  const getFileBadge = (fileType) => {
    switch (fileType?.toLowerCase()) {
      case 'pdf':
        return {
          icon: <FileText className="w-4 h-4 text-rose-400" />,
          bgColor: 'bg-rose-500/10 border-rose-500/30 text-rose-300',
          label: 'PDF',
        };
      case 'docx':
        return {
          icon: <FileText className="w-4 h-4 text-sky-400" />,
          bgColor: 'bg-sky-500/10 border-sky-500/30 text-sky-300',
          label: 'DOCX',
        };
      case 'csv':
        return {
          icon: <FileSpreadsheet className="w-4 h-4 text-amber-400" />,
          bgColor: 'bg-amber-500/10 border-amber-500/30 text-amber-300',
          label: 'CSV',
        };
      case 'txt':
        return {
          icon: <FileCode className="w-4 h-4 text-emerald-400" />,
          bgColor: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300',
          label: 'TXT',
        };
      default:
        return {
          icon: <File className="w-4 h-4 text-slate-400" />,
          bgColor: 'bg-slate-700/50 border-slate-600 text-slate-300',
          label: fileType?.toUpperCase() || 'FILE',
        };
    }
  };

  const formatTimestamp = (timestampStr) => {
    try {
      const date = new Date(timestampStr);
      return date.toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return timestampStr;
    }
  };

  return (
    <div className="w-full glass-panel rounded-2xl p-6 shadow-xl">
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-700/50">
        <div className="flex items-center space-x-3">
          <h3 className="text-base font-semibold text-slate-100">Uploaded Documents</h3>
          <span className="text-xs bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 px-2.5 py-0.5 rounded-full font-medium">
            {documents.length} {documents.length === 1 ? 'file' : 'files'}
          </span>
        </div>

        <button
          onClick={fetchDocuments}
          disabled={loading}
          className="text-xs text-slate-400 hover:text-slate-200 bg-slate-800/80 hover:bg-slate-700/60 px-3 py-1.5 rounded-lg border border-slate-700/60 transition-all flex items-center gap-1.5 disabled:opacity-50"
          title="Refresh document list"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Loading indicator */}
      {loading && documents.length === 0 && (
        <div className="flex flex-col items-center justify-center py-12 text-slate-400 space-y-2">
          <Loader2 className="w-7 h-7 text-indigo-400 animate-spin" />
          <p className="text-xs">Loading uploaded documents...</p>
        </div>
      )}

      {/* Error display */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2 mb-4">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Empty State */}
      {!loading && documents.length === 0 && !error && (
        <div className="text-center py-10 px-4 rounded-xl border border-dashed border-slate-700/60 bg-slate-900/20">
          <FileText className="w-10 h-10 text-slate-600 mx-auto mb-2" />
          <p className="text-sm font-medium text-slate-300">No documents uploaded yet</p>
          <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1">
            Upload PDF, DOCX, TXT, or CSV files above to establish your personal knowledge base for RAG querying.
          </p>
        </div>
      )}

      {/* Documents List */}
      {documents.length > 0 && (
        <div className="space-y-2.5">
          {documents.map((doc) => {
            const badge = getFileBadge(doc.file_type);
            const isFailed = doc.status === 'failed';

            return (
              <div
                key={doc.id}
                className={`p-3.5 rounded-xl border transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                  isFailed
                    ? 'bg-rose-950/20 border-rose-800/40 hover:border-rose-700/60'
                    : 'bg-slate-900/50 border-slate-700/50 hover:border-slate-600'
                }`}
              >
                {/* Left info: Icon, Name, Type, Time */}
                <div className="flex items-start space-x-3 min-w-0">
                  <div className="p-2 rounded-lg bg-slate-800 border border-slate-700/60 shrink-0">
                    {badge.icon}
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-medium text-slate-200 truncate max-w-xs sm:max-w-md" title={doc.original_filename}>
                        {doc.original_filename}
                      </span>
                      <span className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${badge.bgColor}`}>
                        {badge.label}
                      </span>
                    </div>

                    <div className="flex items-center gap-3 text-[11px] text-slate-400 mt-1">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3 text-slate-500" />
                        {formatTimestamp(doc.upload_timestamp)}
                      </span>
                    </div>

                    {/* Failure details if parsing failed */}
                    {isFailed && doc.error_message && (
                      <p className="mt-1.5 text-[11px] text-rose-300 font-mono bg-rose-950/40 border border-rose-800/30 p-1.5 rounded">
                        Error: {doc.error_message}
                      </p>
                    )}

                    {/* Prompt 8: AI Summary display under document filename */}
                    {doc.summary && (
                      <div className="mt-2.5 text-xs text-slate-300 bg-slate-950/40 border border-indigo-500/20 rounded-lg p-2.5 leading-relaxed">
                        <div className="flex items-center gap-1.5 text-[10px] font-semibold text-indigo-400 uppercase tracking-wider mb-1">
                          <Sparkles className="w-3 h-3 text-indigo-400 shrink-0" />
                          <span>AI Summary</span>
                        </div>
                        <p className="text-slate-300">{doc.summary}</p>
                      </div>
                    )}

                    {/* Prompt 8: Subtle placeholder while summary is generating */}
                    {isRecentIndexedWithoutSummary(doc) && (
                      <div className="mt-2 inline-flex items-center gap-1.5 text-xs text-indigo-300/80 italic bg-indigo-950/20 border border-indigo-500/20 px-2.5 py-1 rounded-lg animate-pulse">
                        <Loader2 className="w-3 h-3 text-indigo-400 animate-spin shrink-0" />
                        <span>Generating summary...</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Right info: Status Badge & Delete Button */}
                <div className="flex items-center justify-between sm:justify-end gap-3 shrink-0 pt-2 sm:pt-0 border-t sm:border-t-0 border-slate-800">
                  {isFailed ? (
                    <span className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full bg-rose-500/10 border border-rose-500/30 text-rose-400">
                      <AlertCircle className="w-3.5 h-3.5" />
                      Parsing Failed
                    </span>
                  ) : doc.status === 'indexed' ? (
                    <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Indexed</span>
                      <span className="text-[11px] font-normal text-emerald-300/90 bg-emerald-950/50 px-1.5 py-0.5 rounded border border-emerald-500/20">
                        {doc.chunk_count || 0} {(doc.chunk_count === 1) ? 'chunk' : 'chunks'}
                      </span>
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full bg-sky-500/10 border border-sky-500/30 text-sky-400">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Parsed
                    </span>
                  )}

                  <button
                    onClick={() => handleDelete(doc.id, doc.original_filename)}
                    disabled={deletingId === doc.id}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 bg-slate-800/60 hover:bg-rose-500/10 border border-slate-700/60 hover:border-rose-500/30 transition-all disabled:opacity-50"
                    title="Delete document"
                  >
                    {deletingId === doc.id ? (
                      <Loader2 className="w-4 h-4 animate-spin text-rose-400" />
                    ) : (
                      <Trash2 className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
