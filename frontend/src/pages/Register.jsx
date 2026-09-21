import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, Loader2, AlertCircle, CheckCircle2, User, Lock, Camera, Sparkles } from 'lucide-react';
import { BrandHeader } from '../components/BrandHeader';
import { FaceCapture } from '../components/FaceCapture';
import api from '../services/api';

export const Register = () => {
  const navigate = useNavigate();

  // Registration form inputs
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    confirmPassword: '',
  });

  // Wizard stage: 'form' | 'face_enroll' | 'complete'
  const [stage, setStage] = useState('form');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Face enrollment state
  const [faceLoading, setFaceLoading] = useState(false);
  const [faceError, setFaceError] = useState('');

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
    if (error) setError('');
  };

  const validateForm = () => {
    const { username, password, confirmPassword } = formData;
    const usernameRegex = /^[a-zA-Z0-9_]+$/;

    if (!username || username.length < 3 || username.length > 30) {
      return 'Username must be between 3 and 30 characters long.';
    }
    if (!usernameRegex.test(username)) {
      return 'Username can only contain letters, numbers, and underscores.';
    }
    if (!password || password.length < 6) {
      return 'Password must be at least 6 characters long.';
    }
    if (password !== confirmPassword) {
      return 'Passwords do not match.';
    }
    return null;
  };

  // Step 1: Submit account credentials
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    const validationError = validateForm();
    if (validationError) {
      setError(validationError);
      return;
    }

    setLoading(true);

    try {
      await api.post('/auth/register', {
        username: formData.username.trim(),
        password: formData.password,
      });

      // Advance to face registration step
      setStage('face_enroll');
    } catch (err) {
      if (err.response && err.response.data) {
        const detail = err.response.data.detail || err.response.data.message;
        if (Array.isArray(detail)) {
          setError(detail.map((d) => d.msg).join(', '));
        } else if (typeof detail === 'string') {
          setError(detail);
        } else {
          setError('Registration failed. Please try again.');
        }
      } else {
        setError('Unable to complete registration. Please check your connection to the server.');
      }
    } finally {
      setLoading(false);
    }
  };

  // Step 2: Register face descriptor
  const handleFaceCapture = async (descriptor) => {
    setFaceLoading(true);
    setFaceError('');

    try {
      await api.post('/auth/register-face', {
        username: formData.username.trim(),
        face_descriptor: descriptor,
      });

      setStage('complete');
    } catch (err) {
      console.error('Face registration failure:', err);
      const msg =
        err.response?.data?.message ||
        err.response?.data?.detail ||
        'Failed to save facial recognition data. You can skip and try again later.';
      setFaceError(msg);
    } finally {
      setFaceLoading(false);
    }
  };

  return (
    <div className="auth-page min-h-screen flex items-center justify-center p-4">
      <div className="auth-card w-full max-w-md glass-panel rounded-3xl p-8 shadow-2xl shadow-slate-950/50">
        <Link
          to="/"
          className="inline-flex items-center text-xs font-medium text-slate-400 hover:text-slate-200 transition-colors mb-4"
        >
          <ArrowLeft className="w-4 h-4 mr-1" /> Back to options
        </Link>

        {/* STAGE 1: Standard Account Form */}
        {stage === 'form' && (
          <>
            <BrandHeader subtitle="Create a new account to get started" />

            {error && (
              <div className="mb-6 p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start gap-3 text-rose-300 text-sm">
                <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
                <div>{error}</div>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5 uppercase tracking-wider">
                  Username
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <User className="w-5 h-5" />
                  </div>
                  <input
                    type="text"
                    name="username"
                    value={formData.username}
                    onChange={handleChange}
                    disabled={loading}
                    placeholder="3-30 chars (letters, numbers, _)"
                    className="w-full pl-11 pr-4 py-3 bg-slate-900/80 border border-slate-700 rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 disabled:opacity-50 transition-all text-sm"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5 uppercase tracking-wider">
                  Password
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Lock className="w-5 h-5" />
                  </div>
                  <input
                    type="password"
                    name="password"
                    value={formData.password}
                    onChange={handleChange}
                    disabled={loading}
                    placeholder="Minimum 6 characters"
                    className="w-full pl-11 pr-4 py-3 bg-slate-900/80 border border-slate-700 rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 disabled:opacity-50 transition-all text-sm"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5 uppercase tracking-wider">
                  Confirm Password
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Lock className="w-5 h-5" />
                  </div>
                  <input
                    type="password"
                    name="confirmPassword"
                    value={formData.confirmPassword}
                    onChange={handleChange}
                    disabled={loading}
                    placeholder="Re-enter password"
                    className="w-full pl-11 pr-4 py-3 bg-slate-900/80 border border-slate-700 rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 disabled:opacity-50 transition-all text-sm"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm shadow-lg shadow-indigo-600/30 transition-all flex items-center justify-center disabled:opacity-60 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-indigo-400 mt-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin mr-2" />
                    Creating Account...
                  </>
                ) : (
                  'Create Account'
                )}
              </button>
            </form>

            <div className="mt-8 pt-6 border-t border-slate-700/50 text-center">
              <p className="text-sm text-slate-400">
                Already have an account?{' '}
                <Link
                  to="/login/password"
                  className="font-medium text-indigo-400 hover:text-indigo-300 hover:underline transition-colors"
                >
                  Sign in
                </Link>
              </p>
            </div>
          </>
        )}

        {/* STAGE 2: Face Enrollment Step */}
        {stage === 'face_enroll' && (
          <div>
            <div className="text-center mb-6">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold uppercase tracking-wider mb-2">
                <Sparkles className="w-3.5 h-3.5" /> Step 2 of 2
              </span>
              <h2 className="text-xl font-bold text-slate-100">
                Now let's add your face for quick login
              </h2>
              <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
                Capture your facial biometrics to enable instant passwordless authentication.
              </p>
            </div>

            {faceError && (
              <div className="mb-4 p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start gap-2.5 text-rose-300 text-xs">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                <div>{faceError}</div>
              </div>
            )}

            <FaceCapture
              onCapture={handleFaceCapture}
              buttonText="Register Face"
              isProcessing={faceLoading}
            />

            <div className="mt-4 text-center">
              <button
                type="button"
                onClick={() => navigate('/login/password')}
                className="text-xs font-medium text-slate-400 hover:text-slate-200 transition-colors py-2 px-4 rounded-lg hover:bg-slate-700/30"
              >
                Skip for now
              </button>
            </div>
          </div>
        )}

        {/* STAGE 3: Completed Confirmation */}
        {stage === 'complete' && (
          <div className="p-6 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-center space-y-4">
            <div className="w-14 h-14 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto shadow-lg shadow-emerald-500/20">
              <CheckCircle2 className="w-8 h-8" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-emerald-300">Face Registered Successfully!</h3>
              <p className="text-xs text-slate-300 mt-2 leading-relaxed">
                Your face biometric descriptor is securely saved. You can now log in instantly using facial recognition or your password.
              </p>
            </div>

            <div className="space-y-2 pt-2">
              <button
                onClick={() => navigate('/login/face')}
                className="w-full py-3.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm transition-all shadow-lg shadow-indigo-600/30 flex items-center justify-center gap-2"
              >
                <Camera className="w-4 h-4" />
                Try Face Login Now
              </button>

              <button
                onClick={() => navigate('/login/password')}
                className="w-full py-2.5 px-4 rounded-xl bg-slate-900/60 hover:bg-slate-700/50 text-slate-300 font-medium text-xs border border-slate-700/60 transition-all"
              >
                Go to Password Login
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
