import { m, AnimatePresence, useReducedMotion } from 'motion/react';
import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useUser } from '@clerk/clerk-react';
import {
  ArrowLeft,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  ShieldCheck,
  Plus,
  Trash2,
  ScanFace,
  Loader2,
  Calendar,
  X,
} from 'lucide-react';
import { BrandHeader } from '../components/BrandHeader';
import { FaceCapture } from '../components/FaceCapture';
import api from '../services/api';

export const AddFace = () => {
  const shouldReduceMotion = useReducedMotion();
  const { user: clerkUser } = useUser();
  const navigate = useNavigate();

  const [faces, setFaces] = useState([]);
  const [loadingFaces, setLoadingFaces] = useState(true);
  const [isAdding, setIsAdding] = useState(false);
  const [faceLabel, setFaceLabel] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [deleteConfirmFace, setDeleteConfirmFace] = useState(null);

  const displayName =
    clerkUser?.firstName ||
    clerkUser?.username ||
    clerkUser?.primaryEmailAddress?.emailAddress ||
    'User';

  const fetchFaces = async () => {
    try {
      setLoadingFaces(true);
      const res = await api.get('/auth/faces');
      setFaces(res.data || []);
    } catch (err) {
      console.error('Failed to fetch registered faces:', err);
    } finally {
      setLoadingFaces(false);
    }
  };

  useEffect(() => {
    fetchFaces();
  }, []);

  const handleCaptureFace = async (descriptor) => {
    setLoading(true);
    setError('');
    setSuccessMessage('');

    try {
      const payload = {
        face_descriptor: descriptor,
      };
      if (faceLabel.trim()) {
        payload.label = faceLabel.trim();
      }

      await api.post('/auth/add-face', payload);

      setSuccessMessage(
        faceLabel.trim()
          ? `Face "${faceLabel.trim()}" registered successfully!`
          : 'New face registered successfully!'
      );
      setFaceLabel('');
      setIsAdding(false);
      await fetchFaces();
    } catch (err) {
      console.error('Add face error:', err);
      const msg =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        'Failed to add facial biometric descriptor. Please try again.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const confirmDelete = async () => {
    if (!deleteConfirmFace) return;
    setLoading(true);
    setError('');
    setSuccessMessage('');

    try {
      await api.delete(`/auth/faces/${deleteConfirmFace.id}`);
      setSuccessMessage(`Face "${deleteConfirmFace.label}" deleted.`);
      setDeleteConfirmFace(null);
      await fetchFaces();
    } catch (err) {
      console.error('Delete face error:', err);
      const msg =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        'Failed to delete face registration.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const formatFaceDate = (isoStr) => {
    if (!isoStr) return '';
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return '';
    }
  };

  return (
    <m.div
      initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      exit={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: -15 }}
      transition={{ duration: 0.3 }}
      className="auth-page min-h-screen flex items-center justify-center p-4"
    >
      <div className="auth-card w-full max-w-lg glass-panel rounded-3xl p-6 sm:p-8 shadow-2xl shadow-slate-950/60 relative">
        <div className="flex items-center justify-between mb-4">
          <Link
            to="/chat"
            className="inline-flex items-center text-xs font-medium text-slate-400 hover:text-slate-200 transition-colors"
          >
            <ArrowLeft className="w-4 h-4 mr-1" /> Back to Chat
          </Link>
          <span className="text-xs text-indigo-400 font-semibold bg-indigo-500/10 px-2.5 py-1 rounded-full border border-indigo-500/20 flex items-center gap-1">
            <ScanFace className="w-3.5 h-3.5" /> Biometric Center
          </span>
        </div>

        <BrandHeader subtitle="Manage Face Authentication Profiles" />

        {/* User Identity Info */}
        <div className="mb-5 p-3 rounded-xl bg-slate-800/60 border border-slate-700/60 flex items-center gap-2.5 text-xs text-slate-300">
          <ShieldCheck className="w-4 h-4 shrink-0 text-indigo-400" />
          <span>
            Signed in as <strong className="text-white">{displayName}</strong>. You can register multiple facial profiles for faster sign-in.
          </span>
        </div>

        {/* Notifications */}
        {successMessage && (
          <div className="mb-4 p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-between text-emerald-300 text-xs">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
              <span>{successMessage}</span>
            </div>
            <button
              onClick={() => setSuccessMessage('')}
              className="text-emerald-400/70 hover:text-emerald-300 p-0.5"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {error && (
          <div className="mb-4 p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start gap-2.5 text-rose-300 text-xs">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <div className="flex-1">{error}</div>
            <button
              onClick={() => setError('')}
              className="text-rose-400/70 hover:text-rose-300 p-0.5"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* View Mode: Add New Face vs List Registered Faces */}
        {isAdding ? (
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <Plus className="w-4 h-4 text-indigo-400" /> Register New Face Profile
              </h3>
              <button
                type="button"
                onClick={() => {
                  setIsAdding(false);
                  setFaceLabel('');
                  setError('');
                }}
                className="text-xs text-slate-400 hover:text-white px-2 py-1 rounded-lg hover:bg-slate-800 transition-colors"
              >
                Cancel
              </button>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Profile Label (Optional)
              </label>
              <input
                type="text"
                value={faceLabel}
                onChange={(e) => setFaceLabel(e.target.value)}
                placeholder={`e.g. Work Laptop, Studio, Face ${faces.length + 1}`}
                maxLength={40}
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950/70 border border-slate-700 text-slate-200 text-xs focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
              <p className="text-[11px] text-slate-500 mt-1">
                A custom label helps you distinguish multiple faces or devices.
              </p>
            </div>

            {/* Live Camera Viewfinder & Extraction */}
            <FaceCapture
              onCapture={handleCaptureFace}
              buttonText="Capture & Save Face"
              isProcessing={loading}
              disabled={loading}
            />
          </div>
        ) : (
          <div className="space-y-4">
            {/* Header with Add Button */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-semibold text-slate-200">
                  Registered Faces
                </h3>
                <span className="text-[11px] bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 px-2 py-0.5 rounded-full font-semibold">
                  {faces.length}
                </span>
              </div>
              <button
                type="button"
                onClick={() => {
                  setIsAdding(true);
                  setError('');
                  setSuccessMessage('');
                }}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs shadow-md shadow-indigo-600/25 transition-all active:scale-95"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add Face</span>
              </button>
            </div>

            {/* Face List */}
            {loadingFaces ? (
              <div className="py-10 text-center text-slate-500 text-xs flex items-center justify-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
                <span>Loading face profiles...</span>
              </div>
            ) : faces.length === 0 ? (
              <div className="p-6 rounded-2xl bg-slate-950/40 border border-dashed border-slate-800 text-center space-y-3">
                <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center mx-auto">
                  <ScanFace className="w-6 h-6" />
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-slate-300">No Faces Registered Yet</h4>
                  <p className="text-xs text-slate-500 mt-1 max-w-xs mx-auto">
                    Add a biometric face profile to sign in seamlessly without typing passwords.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setIsAdding(true)}
                  className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md shadow-indigo-600/25 transition-all"
                >
                  Register Your First Face
                </button>
              </div>
            ) : (
              <div className="space-y-2.5 max-h-72 overflow-y-auto pr-1">
                {faces.map((f, idx) => (
                  <div
                    key={f.id}
                    className="p-3.5 rounded-xl bg-slate-800/70 border border-slate-700/60 flex items-center justify-between gap-3 group hover:border-slate-600 transition-colors"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600/30 to-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center shrink-0">
                        <ScanFace className="w-5 h-5" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-xs font-semibold text-slate-200 truncate">
                          {f.label || `Face ${idx + 1}`}
                        </p>
                        <p className="text-[10px] text-slate-400 flex items-center gap-1 mt-0.5">
                          <Calendar className="w-3 h-3" />
                          <span>{formatFaceDate(f.created_at)}</span>
                        </p>
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() => setDeleteConfirmFace(f)}
                      title="Delete this face profile"
                      className="p-2 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-all"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Delete Confirmation Modal */}
        {deleteConfirmFace && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur-xs flex items-center justify-center p-4 z-50">
            <div className="w-full max-w-sm glass-panel border border-white/10 rounded-2xl p-5 shadow-2xl space-y-4">
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${faces.length === 1 ? 'bg-amber-500/20 text-amber-400' : 'bg-rose-500/20 text-rose-400'}`}>
                  {faces.length === 1 ? (
                    <AlertTriangle className="w-5 h-5" />
                  ) : (
                    <Trash2 className="w-5 h-5" />
                  )}
                </div>
                <div>
                  <h4 className="text-sm font-bold text-white">
                    {faces.length === 1 ? 'Delete Only Registered Face?' : 'Delete Face Profile?'}
                  </h4>
                  <p className="text-xs text-slate-400 truncate max-w-[200px]">
                    {deleteConfirmFace.label}
                  </p>
                </div>
              </div>

              {faces.length === 1 ? (
                <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-300 leading-relaxed">
                  <strong>Warning:</strong> This is your only registered face. After deleting, you'll need to sign in with email/Google instead of face recognition. Continue?
                </div>
              ) : (
                <p className="text-xs text-slate-300 leading-relaxed">
                  Are you sure you want to delete this facial profile? You can still sign in using any of your other registered faces.
                </p>
              )}

              <div className="flex items-center gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => setDeleteConfirmFace(null)}
                  disabled={loading}
                  className="flex-1 py-2 px-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={confirmDelete}
                  disabled={loading}
                  className="flex-1 py-2 px-3 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold shadow-md shadow-rose-600/30 transition-colors disabled:opacity-50 flex items-center justify-center gap-1.5"
                >
                  {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
                  <span>Confirm Delete</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </m.div>
  );
};

export default AddFace;
