import React, { useState, useRef } from 'react';
import { UploadCloud, FileText, CheckCircle2, AlertCircle, AlertTriangle, Loader2, X } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

/**
 * UploadDocument Component
 *
 * Provides a drag-and-drop file upload zone and file picker for
 * documents in .pdf, .docx, .txt, and .csv formats.
 *
 * Validations:
 * 1. Checks file extension before upload against allowed set.
 * 2. Checks file size against 50MB limit before sending.
 * 3. Shows live loading/progress state while upload/parsing takes place.
 * 4. Distinctly handles both HTTP errors and backend 200 "failed" parse statuses.
 */
export const UploadDocument = ({ onUploadSuccess }) => {
  const { user } = useAuth();
  const fileInputRef = useRef(null);

  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [feedback, setFeedback] = useState(null); // { type: 'success' | 'error' | 'warning', message: string, details?: string }
  const [selectedFileName, setSelectedFileName] = useState(null);

  const ALLOWED_EXTENSIONS = ['pdf', 'docx', 'txt', 'csv'];
  const MAX_SIZE_BYTES = 50 * 1024 * 1024; // 50MB

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processAndUploadFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      processAndUploadFile(e.target.files[0]);
    }
  };

  const processAndUploadFile = async (file) => {
    setFeedback(null);
    setSelectedFileName(file.name);

    // 1. Client-side extension validation
    const ext = file.name.split('.').pop().toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setFeedback({
        type: 'error',
        message: 'Unsupported file type. Please upload PDF, DOCX, TXT, or CSV.',
      });
      return;
    }

    // 2. Client-side file size validation (50MB)
    if (file.size > MAX_SIZE_BYTES) {
      setFeedback({
        type: 'error',
        message: 'File size exceeds the 50MB limit. Please upload a smaller file.',
      });
      return;
    }

    // 3. Initiate multipart/form-data upload
    setUploading(true);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await api.post('/documents/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      const result = response.data;

      // Reset file input value so user can upload same file again if desired
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }

      if (result.status === 'indexed' || result.status === 'parsed') {
        const chunkMsg = result.chunk_count ? ` (${result.chunk_count} chunks indexed)` : '';
        setFeedback({
          type: 'success',
          message: `"${result.filename}" uploaded and indexed successfully!${chunkMsg}`,
        });
        if (onUploadSuccess) {
          onUploadSuccess(result);
        }
      } else {
        // Document record was stored but parsing failed (corrupt, empty, etc.)
        setFeedback({
          type: 'warning',
          message: `Document "${result.filename}" uploaded, but parsing failed:`,
          details: result.error_message || 'Unreadable or unsupported document structure.',
        });
        if (onUploadSuccess) {
          onUploadSuccess(result);
        }
      }
    } catch (err) {
      console.error('Upload error:', err);
      const serverError =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        'Failed to connect to the document processing server.';
      setFeedback({
        type: 'error',
        message: serverError,
      });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="w-full glass-panel rounded-2xl p-6 shadow-xl">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4 pb-3 border-b border-slate-700/50">
        <div>
          <h2 className="text-base font-semibold text-slate-100 flex items-center gap-2">
            <UploadCloud className="w-5 h-5 text-indigo-400" />
            Upload Knowledge Base Document
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Supported formats: <span className="text-indigo-300 font-medium">.pdf, .docx, .txt, .csv</span> (Max 50MB)
          </p>
        </div>
        <div className="flex items-center text-xs text-slate-400 bg-slate-900/60 px-3 py-1.5 rounded-lg border border-slate-700/60 w-fit">
          <span>Uploading as:</span>
          <span className="font-mono text-indigo-300 font-semibold ml-1.5">{user}</span>
        </div>
      </div>

      {/* Drag & Drop Zone */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => !uploading && fileInputRef.current?.click()}
        className={`relative border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-200 flex flex-col items-center justify-center ${
          dragActive
            ? 'border-indigo-500 bg-indigo-500/10 scale-[1.005]'
            : 'border-slate-700 hover:border-indigo-500/50 hover:bg-slate-800/80 bg-slate-900/30'
        } ${uploading ? 'pointer-events-none opacity-60' : ''}`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.txt,.csv"
          onChange={handleFileInputChange}
          className="hidden"
          disabled={uploading}
        />

        {uploading ? (
          <div className="flex flex-col items-center space-y-3 py-2">
            <div className="w-12 h-12 rounded-2xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 animate-spin">
              <Loader2 className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-200">
                Parsing & Ingesting <span className="font-mono text-indigo-300">{selectedFileName}</span>...
              </p>
              <p className="text-xs text-slate-400 mt-1">Extracting raw text into SQLite storage</p>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center space-y-3 py-2">
            <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 group-hover:scale-110 transition-transform">
              <FileText className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-200">
                <span className="text-indigo-400 hover:underline">Click to browse</span> or drag and drop your file here
              </p>
              <p className="text-xs text-slate-500 mt-1">
                PDF, Word (.docx), Plain Text (.txt), or CSV tables up to 50MB
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Live Feedback Messages */}
      {feedback && (
        <div
          className={`mt-4 p-4 rounded-xl text-xs flex items-start justify-between gap-3 border ${
            feedback.type === 'success'
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
              : feedback.type === 'warning'
              ? 'bg-amber-500/10 border-amber-500/30 text-amber-300'
              : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
          }`}
        >
          <div className="flex items-start gap-2.5">
            {feedback.type === 'success' && <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5 text-emerald-400" />}
            {feedback.type === 'warning' && <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-amber-400" />}
            {feedback.type === 'error' && <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-400" />}
            <div>
              <p className="font-semibold">{feedback.message}</p>
              {feedback.details && (
                <p className="mt-1 font-mono text-[11px] bg-slate-900/50 p-2 rounded border border-slate-700/50 break-all text-slate-300">
                  {feedback.details}
                </p>
              )}
            </div>
          </div>
          <button
            onClick={() => setFeedback(null)}
            className="text-slate-400 hover:text-slate-200 p-0.5"
            title="Dismiss"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  );
};
