import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, Loader2, AlertCircle, Lock, User } from 'lucide-react';
import { m, AnimatePresence, useReducedMotion } from 'motion/react';
import { BrandHeader } from '../components/BrandHeader';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

export const PasswordLogin = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const shouldReduceMotion = useReducedMotion();

  const [formData, setFormData] = useState({
    username: '',
    password: '',
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
    if (error) setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!formData.username.trim() || !formData.password.trim()) {
      setError('Please enter both username and password.');
      return;
    }

    setLoading(true);

    try {
      const response = await api.post('/auth/login/password', {
        username: formData.username.trim(),
        password: formData.password,
      });

      if (response.data && response.data.username) {
        login(response.data.username, 'password');
        navigate('/chat');
      }
    } catch (err) {
      if (err.response && err.response.data && err.response.data.detail) {
        // Show generic friendly error message from backend without revealing which credential failed
        setError(err.response.data.detail);
      } else {
        setError('Unable to connect to authentication server. Please check your connection.');
      }
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
      <div className="auth-card w-full max-w-md glass-panel rounded-3xl p-8">
        <Link
          to="/"
          className="inline-flex items-center text-xs font-medium text-slate-400 hover:text-slate-200 transition-colors mb-4"
        >
          <ArrowLeft className="w-4 h-4 mr-1" /> Back to options
        </Link>

        <BrandHeader subtitle="Enter your credentials to sign in" />

        <AnimatePresence>
          {error && (
            <m.div
              initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, height: 0, marginBottom: 0 }}
              animate={shouldReduceMotion ? { opacity: 1 } : { opacity: 1, height: 'auto', marginBottom: 24 }}
              exit={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, height: 0, marginBottom: 0 }}
              className="overflow-hidden"
            >
              <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start gap-3 text-rose-300 text-sm">
                <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
                <div>{error}</div>
              </div>
            </m.div>
          )}
        </AnimatePresence>

        <form onSubmit={handleSubmit} className="space-y-5">
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
                placeholder="Enter your username"
                className="w-full pl-11 pr-4 py-3 bg-white/5 border border-white/10 rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-violet-500 focus:border-violet-500 disabled:opacity-50 transition-all text-sm"
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
                placeholder="Enter your password"
                className="w-full pl-11 pr-4 py-3 bg-white/5 border border-white/10 rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-violet-500 focus:border-violet-500 disabled:opacity-50 transition-all text-sm"
              />
            </div>
          </div>

          <m.button
            whileHover={shouldReduceMotion || loading ? {} : { scale: 1.02 }}
            whileTap={shouldReduceMotion || loading ? {} : { scale: 0.98 }}
            type="submit"
            disabled={loading}
            className="w-full h-[50px] rounded-xl bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 text-white font-semibold text-sm shadow-lg shadow-violet-600/30 transition-all flex items-center justify-center disabled:opacity-60 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-violet-400 relative overflow-hidden"
          >
            {loading ? (
              <div className="flex items-center justify-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-white" />
                <span>Signing in...</span>
              </div>
            ) : (
              <span>Sign In with Password</span>
            )}
          </m.button>
        </form>

        <div className="mt-8 pt-6 border-t border-white/10 text-center">
          <p className="text-sm text-slate-400">
            Don't have an account?{' '}
            <Link
              to="/register"
              className="font-medium text-violet-400 hover:text-fuchsia-300 hover:underline transition-colors"
            >
              Register
            </Link>
          </p>
        </div>
      </div>
    </m.div>
  );
};
