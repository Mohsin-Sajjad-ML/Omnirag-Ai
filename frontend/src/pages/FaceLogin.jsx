import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Camera, KeyRound, ArrowLeft, AlertCircle, RefreshCw, Sparkles } from 'lucide-react';
import { BrandHeader } from '../components/BrandHeader';
import { FaceCapture } from '../components/FaceCapture';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

export const FaceLogin = () => {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(false);
  const [errorState, setErrorState] = useState(null); // null | 'unrecognized' | error string

  const handleFaceCapture = async (descriptor) => {
    setLoading(true);
    setErrorState(null);

    try {
      const response = await api.post('/auth/login/face', {
        face_descriptor: descriptor,
      });

      if (response.data && response.data.username) {
        // Biometric match successful: store username and login method in AuthContext and go to chat
        login(response.data.username, 'face');
        navigate('/chat');
      } else {
        setErrorState('unrecognized');
      }
    } catch (err) {
      console.warn('Face login error:', err);
      // Backend returns 401 with { message: "Face not recognized" }
      if (err.response && err.response.status === 401) {
        setErrorState('unrecognized');
      } else {
        setErrorState(
          err.response?.data?.message ||
            err.response?.data?.detail ||
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
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-slate-800/80 backdrop-blur-xl border border-slate-700/60 rounded-3xl p-8 shadow-2xl shadow-slate-950/50">
        <Link
          to="/"
          className="inline-flex items-center text-xs font-medium text-slate-400 hover:text-slate-200 transition-colors mb-4"
        >
          <ArrowLeft className="w-4 h-4 mr-1" /> Back to options
        </Link>

        <BrandHeader subtitle="Biometric Facial Recognition Authentication" />

        {/* Failure Screen: Face Not Recognized */}
        {errorState === 'unrecognized' ? (
          <div className="my-4 p-6 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-center space-y-4">
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
              <button
                type="button"
                onClick={handleReset}
                className="w-full py-3 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm transition-all shadow-lg shadow-indigo-600/30 flex items-center justify-center gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                Try Again
              </button>

              <Link
                to="/login/password"
                className="w-full py-3 px-4 rounded-xl bg-slate-900/80 hover:bg-slate-700/60 text-slate-200 font-medium text-sm border border-slate-700/80 transition-all flex items-center justify-center gap-2"
              >
                <KeyRound className="w-4 h-4" />
                Use Password Instead
              </Link>
            </div>
          </div>
        ) : (
          <div>
            {/* Generic Server Error Alert */}
            {errorState && errorState !== 'unrecognized' && (
              <div className="mb-4 p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start gap-3 text-rose-300 text-sm">
                <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
                <div>{errorState}</div>
              </div>
            )}

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
    </div>
  );
};
