import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Lock, ArrowLeft, CheckCircle2, AlertCircle, ShieldCheck, Loader2 } from 'lucide-react';
import { BrandHeader } from '../components/BrandHeader';
import { FaceCapture } from '../components/FaceCapture';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

export const AddFace = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleCaptureFace = async (descriptor) => {
    if (!password.trim()) {
      setError('Please enter your current password to confirm your identity before updating face biometrics.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      await api.post('/auth/add-face', {
        username: user,
        password: password,
        face_descriptor: descriptor,
      });

      setSuccess(true);
    } catch (err) {
      console.error('Update face error:', err);
      const msg =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        'Failed to update facial biometric descriptor. Please verify your password.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-slate-800/80 backdrop-blur-xl border border-slate-700/60 rounded-3xl p-8 shadow-2xl shadow-slate-950/50">
        <Link
          to="/chat"
          className="inline-flex items-center text-xs font-medium text-slate-400 hover:text-slate-200 transition-colors mb-4"
        >
          <ArrowLeft className="w-4 h-4 mr-1" /> Back to Chat
        </Link>

        <BrandHeader subtitle="Manage Biometric Face Authentication" />

        {success ? (
          <div className="p-6 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-center space-y-4">
            <div className="w-14 h-14 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto shadow-lg shadow-emerald-500/20">
              <CheckCircle2 className="w-8 h-8" />
            </div>

            <div>
              <h3 className="text-xl font-bold text-emerald-300">Face Updated Successfully!</h3>
              <p className="text-xs text-slate-300 mt-2 leading-relaxed">
                Your new face descriptor has been verified and saved for <span className="font-semibold text-white">"{user}"</span>. You can now use facial recognition to sign in.
              </p>
            </div>

            <button
              type="button"
              onClick={() => navigate('/chat')}
              className="w-full py-3.5 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-sm transition-all shadow-lg shadow-emerald-600/30"
            >
              Return to Chat
            </button>
          </div>
        ) : (
          <div>
            <div className="mb-5 p-3.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center gap-2.5 text-xs text-indigo-300">
              <ShieldCheck className="w-4 h-4 shrink-0 text-indigo-400" />
              <span>
                Logged in as <strong className="text-white">{user}</strong>. Password confirmation is required to update biometrics.
              </span>
            </div>

            {error && (
              <div className="mb-4 p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start gap-2.5 text-rose-300 text-xs">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                <div>{error}</div>
              </div>
            )}

            {/* Password confirmation input */}
            <div className="mb-5">
              <label className="block text-xs font-medium text-slate-300 mb-1.5 uppercase tracking-wider">
                Current Password <span className="text-rose-400">*</span>
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <Lock className="w-5 h-5" />
                </div>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    if (error) setError('');
                  }}
                  disabled={loading}
                  placeholder="Enter current password to authorize update"
                  className="w-full pl-11 pr-4 py-3 bg-slate-900/80 border border-slate-700 rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 disabled:opacity-50 transition-all text-sm"
                />
              </div>
            </div>

            {/* Live Camera Viewfinder & Face Extraction */}
            <FaceCapture
              onCapture={handleCaptureFace}
              buttonText="Confirm Password & Update Face"
              isProcessing={loading}
              disabled={!password.trim()}
            />

            {!password.trim() && (
              <p className="text-[11px] text-amber-400/80 text-center mt-2 font-medium">
                Please enter your password above to enable face capture.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
