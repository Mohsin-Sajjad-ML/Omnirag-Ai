import { m, AnimatePresence, useReducedMotion } from 'motion/react';
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUser } from '@clerk/clerk-react';
import { CheckCircle2, AlertCircle, Sparkles, ArrowRight } from 'lucide-react';
import { BrandHeader } from '../components/BrandHeader';
import { FaceCapture } from '../components/FaceCapture';
import api from '../services/api';

export const RegisterFace = () => {
  const shouldReduceMotion = useReducedMotion();
  const { user: clerkUser } = useUser();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const displayName =
    clerkUser?.firstName ||
    clerkUser?.username ||
    clerkUser?.primaryEmailAddress?.emailAddress ||
    'there';

  const handleSkip = () => {
    if (clerkUser?.id) {
      sessionStorage.setItem(`face_enrolled_${clerkUser.id}`, 'skipped');
    }
    navigate('/chat');
  };

  const handleFaceCapture = async (descriptor) => {
    setLoading(true);
    setError('');

    try {
      await api.post('/auth/register-face', {
        face_descriptor: descriptor,
      });

      if (clerkUser?.id) {
        sessionStorage.setItem(`face_enrolled_${clerkUser.id}`, 'registered');
      }
      setSuccess(true);
    } catch (err) {
      console.error('Face registration failure:', err);
      const msg =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        'Failed to save facial recognition data. You can skip and try again later.';
      setError(msg);
    } finally {
      setLoading(false);
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
      <div className="auth-card w-full max-w-md glass-panel rounded-3xl p-8 shadow-2xl shadow-slate-950/50">
        <BrandHeader subtitle="Biometric Face Authentication" />

        {success ? (
          <div className="p-6 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-center space-y-4">
            <div className="w-14 h-14 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto shadow-lg shadow-emerald-500/20">
              <CheckCircle2 className="w-8 h-8" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-emerald-300">Face Registered Successfully!</h3>
              <p className="text-xs text-slate-300 mt-2 leading-relaxed">
                Your face biometric descriptor is securely saved. You can now use facial recognition for quick access.
              </p>
            </div>

            <button
              type="button"
              onClick={() => navigate('/chat')}
              className="w-full py-3.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm transition-all shadow-lg shadow-indigo-600/30 flex items-center justify-center gap-2"
            >
              <span>Continue to Chat</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <div>
            <div className="text-center mb-6">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold uppercase tracking-wider mb-2">
                <Sparkles className="w-3.5 h-3.5" /> Quick Face Enrollment
              </span>
              <h2 className="text-xl font-bold text-slate-100">
                Welcome, {displayName}!
              </h2>
              <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
                Register your face now to enable seamless biometric login in the future.
              </p>
            </div>

            <AnimatePresence>
              {error && (
                <m.div
                  initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, height: 0, marginBottom: 0 }}
                  animate={shouldReduceMotion ? { opacity: 1 } : { opacity: 1, height: 'auto', marginBottom: 16 }}
                  exit={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, height: 0, marginBottom: 0 }}
                  className="overflow-hidden"
                >
                  <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start gap-2.5 text-rose-300 text-xs">
                    <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                    <div>{error}</div>
                  </div>
                </m.div>
              )}
            </AnimatePresence>

            <FaceCapture
              onCapture={handleFaceCapture}
              buttonText="Register Face"
              isProcessing={loading}
              disabled={loading}
            />

            <div className="mt-4 text-center">
              <button
                type="button"
                onClick={handleSkip}
                disabled={loading}
                className="text-xs font-medium text-slate-400 hover:text-slate-200 transition-colors py-2 px-4 rounded-lg hover:bg-slate-700/30"
              >
                Skip for now
              </button>
            </div>
          </div>
        )}
      </div>
    </m.div>
  );
};

export default RegisterFace;
