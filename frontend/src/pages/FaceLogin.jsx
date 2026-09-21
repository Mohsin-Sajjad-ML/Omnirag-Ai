import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Camera, KeyRound, ArrowLeft, AlertCircle, RefreshCw, Sparkles, CheckCircle2 } from 'lucide-react';
import { useSignIn } from '@clerk/clerk-react';
import { m, AnimatePresence, useReducedMotion } from 'motion/react';
import { BrandHeader } from '../components/BrandHeader';
import { FaceCapture } from '../components/FaceCapture';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

export const FaceLogin = () => {
  const { login } = useAuth();
  const { isLoaded: isSignInLoaded, signIn, setActive } = useSignIn();
  const navigate = useNavigate();
  const shouldReduceMotion = useReducedMotion();

  const [loading, setLoading] = useState(false);
  const [errorState, setErrorState] = useState(null); // null | 'unrecognized' | error string
  const [successUser, setSuccessUser] = useState(null);

  const handleFaceCapture = async (descriptor) => {
    setLoading(true);
    setErrorState(null);

    try {
      const response = await api.post('/auth/login/face', {
        face_descriptor: descriptor,
      });

      const matchedUser = response.data?.clerk_user_id || response.data?.username;
      const signInToken = response.data?.sign_in_token;

      if (matchedUser) {
        setSuccessUser(matchedUser);

        if (signInToken && isSignInLoaded && signIn && setActive) {
          try {
            const signInAttempt = await signIn.create({
              strategy: 'ticket',
              ticket: signInToken,
            });
            if (signInAttempt.status === 'complete') {
              await setActive({ session: signInAttempt.createdSessionId });
            } else {
              console.warn('Clerk ticket sign-in status not complete:', signInAttempt.status);
            }
          } catch (clerkErr) {
            console.error('Failed to activate Clerk session with token:', clerkErr);
          }
        }

        // Record face authentication in AuthContext & sessionStorage after Clerk is ready
        sessionStorage.setItem(`face_enrolled_${matchedUser}`, 'registered');
        sessionStorage.setItem('face_authenticated', 'true');
        login(matchedUser, 'face');

        setTimeout(() => {
          navigate('/chat');
        }, 900);
      } else {
        setErrorState('unrecognized');
      }
    } catch (err) {
      console.warn('Face login error:', err);
      // Backend returns 401 with { message: "Face not recognized" }
      if (err.response && err.response.status === 401) {
        setErrorState('unrecognized');
      } else {
        const statusMessage = err.response?.status
          ? `Authentication server returned an unexpected error (${err.response.status}). Please try again.`
          : null;
        setErrorState(
          err.response?.data?.message ||
            err.response?.data?.detail ||
            statusMessage ||
            'Unable to communicate with the authentication server. Please check your network connection.'
        );
      }
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setErrorState(null);
  };

  return (
    <m.div
      initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      exit={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: -15 }}
      transition={{ duration: 0.3 }}
      className="auth-page min-h-screen flex items-center justify-center p-4"
    >
      <div className="auth-card w-full max-w-md glass-panel rounded-3xl p-8">
        <Link
          to="/"
          className="inline-flex items-center text-xs font-medium text-slate-400 hover:text-slate-200 transition-colors mb-4"
        >
          <ArrowLeft className="w-4 h-4 mr-1" /> Back to options
        </Link>

        <BrandHeader subtitle="Biometric Facial Recognition Authentication" />

        {/* Success Screen: Animated checkmark */}
        {successUser ? (
          <m.div
            initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.85 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={shouldReduceMotion ? { duration: 0 } : { type: 'spring', stiffness: 350, damping: 24 }}
            className="my-6 p-8 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-center space-y-4 glass-panel"
          >
            <m.div
              initial={shouldReduceMotion ? { scale: 1 } : { scale: 0 }}
              animate={{ scale: 1 }}
              transition={shouldReduceMotion ? { duration: 0 } : { type: 'spring', stiffness: 400, damping: 16, delay: 0.1 }}
              className="w-16 h-16 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto shadow-lg shadow-emerald-500/30 border border-emerald-500/40"
            >
              <CheckCircle2 className="w-10 h-10" />
            </m.div>

            <div>
              <h3 className="text-xl font-bold text-white">Face Verified!</h3>
              <p className="text-xs text-emerald-300 mt-1.5">
                Welcome back, <strong className="text-white">{successUser}</strong>. Directing to chat...
              </p>
            </div>
          </m.div>
        ) : errorState === 'unrecognized' ? (
          /* Failure Screen: Face Not Recognized with gentle shake */
          <m.div 
            initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.95 }}
            animate={
              shouldReduceMotion
                ? { opacity: 1 }
                : {
                    opacity: 1,
                    scale: 1,
                    x: [0, -12, 12, -8, 8, -4, 4, 0],
                  }
            }
            transition={
              shouldReduceMotion
                ? { duration: 0 }
                : { duration: 0.55, ease: 'easeInOut' }
            }
            className="my-4 p-6 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-center space-y-4 glass-panel"
          >
            <div className="w-14 h-14 rounded-full bg-rose-500/20 text-rose-400 flex items-center justify-center mx-auto shadow-lg shadow-rose-500/20">
              <AlertCircle className="w-8 h-8" />
            </div>

            <div>
              <h3 className="text-lg font-bold text-rose-300">Face Not Recognized</h3>
              <p className="text-xs text-slate-300 mt-1 max-w-xs mx-auto leading-relaxed">
                We couldn't match your face with any registered account. Please check your lighting, align your face, or log in with your password.
              </p>
            </div>

            <div className="space-y-2.5 pt-2">
              <m.button
                whileHover={shouldReduceMotion ? {} : { scale: 1.02 }}
                whileTap={shouldReduceMotion ? {} : { scale: 0.98 }}
                type="button"
                onClick={handleReset}
                className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 text-white font-semibold text-sm transition-all shadow-lg shadow-violet-600/30 flex items-center justify-center gap-2 cursor-pointer"
              >
                <RefreshCw className="w-4 h-4" />
                Try Again
              </m.button>

              <Link
                to="/sign-in"
                className="w-full py-3 px-4 rounded-xl bg-white/5 hover:bg-white/10 text-slate-200 font-medium text-sm border border-white/10 transition-all flex items-center justify-center gap-2"
              >
                <KeyRound className="w-4 h-4" />
                Use Password Instead
              </Link>
            </div>
          </m.div>
        ) : (
          <div>
            {/* Generic Server Error Alert */}
            <AnimatePresence>
              {errorState && errorState !== 'unrecognized' && (
                <m.div
                  initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, height: 0, marginBottom: 0 }}
                  animate={shouldReduceMotion ? { opacity: 1 } : { opacity: 1, height: 'auto', marginBottom: 16 }}
                  exit={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, height: 0, marginBottom: 0 }}
                  className="overflow-hidden"
                >
                  <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start gap-3 text-rose-300 text-sm">
                    <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
                    <div>{errorState}</div>
                  </div>
                </m.div>
              )}
            </AnimatePresence>

            {/* Live Camera Viewfinder & Face Detection */}
            <FaceCapture
              onCapture={handleFaceCapture}
              buttonText="Scan & Sign In"
              isProcessing={loading}
            />

            <div className="mt-6 pt-5 border-t border-slate-700/50 flex flex-col items-center gap-2 text-center">
              <Link
                to="/login/password"
                className="text-xs font-medium text-indigo-400 hover:text-indigo-300 hover:underline flex items-center gap-1.5 transition-colors"
              >
                <KeyRound className="w-3.5 h-3.5" />
                Sign in with Password instead
              </Link>

              <p className="text-[11px] text-slate-500">
                Ensure your face is centered and clearly lit for best accuracy.
              </p>
            </div>
          </div>
        )}
      </div>
    </m.div>
  );
};
