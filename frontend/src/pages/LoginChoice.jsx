import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Camera, KeyRound, UserPlus, CheckCircle2, X, ChevronRight, Sparkles } from 'lucide-react';
import { useUser } from '@clerk/clerk-react';
import { m, useReducedMotion } from 'motion/react';
import { BrandHeader } from '../components/BrandHeader';
import { useAuth } from '../context/AuthContext';

export const LoginChoice = () => {
  const navigate = useNavigate();
  const shouldReduceMotion = useReducedMotion();
  const { isAuthenticated } = useAuth();
  const { isSignedIn } = useUser();
  const [deletedNotice, setDeletedNotice] = useState('');

  useEffect(() => {
    const notice = sessionStorage.getItem('account_deleted_notice');
    if (notice) {
      setDeletedNotice(notice);
      sessionStorage.removeItem('account_deleted_notice');
    }
  }, []);

  useEffect(() => {
    if (isAuthenticated || isSignedIn) {
      navigate('/chat', { replace: true });
    }
  }, [isAuthenticated, isSignedIn, navigate]);

  return (
    <m.div
      initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      exit={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: -15 }}
      transition={{ duration: 0.3 }}
      className="auth-page min-h-screen flex items-center justify-center p-4 relative"
    >
      <div className="relative w-full max-w-md">
        {/* Dynamic luminous ambient aura behind auth card */}
        <div className="absolute -inset-1.5 bg-gradient-to-r from-violet-600/35 via-fuchsia-600/35 to-cyan-500/30 rounded-[2.25rem] blur-2xl opacity-75 -z-10 pointer-events-none animate-pulse" />

        <div className="auth-card w-full glass-panel rounded-3xl p-8 border border-violet-500/30 shadow-2xl relative z-10">
          <div className="flex justify-center mb-3">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-medium bg-white/5 border border-violet-500/25 text-violet-300 shadow-sm backdrop-blur-md">
              <Sparkles className="w-3 h-3 text-fuchsia-400" />
              <span>Intelligent Knowledge Platform</span>
            </span>
          </div>

          <m.div
            initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.4 }}
          >
            <BrandHeader subtitle="Select your preferred authentication method to continue" />
          </m.div>

          {deletedNotice && (
            <div className="mb-5 p-3.5 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-start gap-2.5 text-xs text-emerald-300">
              <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400 mt-0.5" />
              <div className="flex-1">{deletedNotice}</div>
              <button
                onClick={() => setDeletedNotice('')}
                className="text-emerald-400/60 hover:text-emerald-300 p-0.5"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          <div className="space-y-4">
            <m.button
              whileHover={shouldReduceMotion ? {} : { scale: 1.02 }}
              whileTap={shouldReduceMotion ? {} : { scale: 0.98 }}
              onClick={() => navigate('/login/face')}
              className="glass-panel w-full group relative flex items-center justify-between p-4 sm:p-5 rounded-2xl hover:bg-white/10 border border-violet-500/20 hover:border-violet-500/60 hover:shadow-[0_0_22px_rgba(139,92,246,0.3)] transition-all text-left focus:outline-none focus:ring-2 focus:ring-violet-500/50"
            >
              <div className="flex items-center space-x-4 min-w-0 flex-1 pr-3">
                <div className="w-12 h-12 rounded-xl bg-violet-500/20 border border-violet-500/40 flex items-center justify-center text-violet-300 group-hover:bg-gradient-to-tr group-hover:from-violet-600 group-hover:to-fuchsia-600 group-hover:text-white transition-all shadow-sm shrink-0">
                  <Camera className="w-6 h-6" />
                </div>
                <div className="min-w-0 flex-1">
                  <h3 className="text-sm sm:text-base font-semibold text-slate-100 group-hover:text-violet-300 transition-colors">
                    Login with Face
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5 leading-normal">
                    Quick biometric sign-in
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <span className="text-[11px] font-semibold text-fuchsia-300 bg-fuchsia-500/15 px-2.5 py-0.5 rounded-full border border-fuchsia-500/30">
                  Biometric
                </span>
                <ChevronRight className="w-4 h-4 text-slate-500 group-hover:text-violet-300 group-hover:translate-x-0.5 transition-all" />
              </div>
            </m.button>

            <m.button
              whileHover={shouldReduceMotion ? {} : { scale: 1.02 }}
              whileTap={shouldReduceMotion ? {} : { scale: 0.98 }}
              onClick={() => navigate('/sign-in')}
              className="glass-panel w-full group relative flex items-center justify-between p-4 sm:p-5 rounded-2xl hover:bg-white/10 border border-white/10 hover:border-fuchsia-500/60 hover:shadow-[0_0_22px_rgba(217,70,239,0.25)] transition-all text-left focus:outline-none focus:ring-2 focus:ring-violet-500/50"
            >
              <div className="flex items-center space-x-4 min-w-0 flex-1 pr-3">
                <div className="w-12 h-12 rounded-xl bg-white/10 border border-white/20 flex items-center justify-center text-slate-200 group-hover:bg-gradient-to-tr group-hover:from-violet-600 group-hover:to-fuchsia-600 group-hover:text-white transition-all shadow-sm shrink-0">
                  <KeyRound className="w-6 h-6" />
                </div>
                <div className="min-w-0 flex-1">
                  <h3 className="text-sm sm:text-base font-semibold text-slate-100 group-hover:text-violet-300 transition-colors">
                    Login with Account / Password
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5 leading-normal">
                    Sign in with Clerk, Google, or password
                  </p>
                </div>
              </div>
              <ChevronRight className="w-4 h-4 text-slate-500 group-hover:text-violet-300 group-hover:translate-x-0.5 transition-all shrink-0" />
            </m.button>
          </div>

          <div className="mt-8 pt-6 border-t border-white/10 text-center">
            <p className="text-sm text-slate-400">
              Don't have an account?{' '}
              <Link
                to="/sign-up"
                className="font-medium text-violet-400 hover:text-fuchsia-300 hover:underline inline-flex items-center gap-1 transition-colors"
              >
                <UserPlus className="w-4 h-4" />
                Register
              </Link>
            </p>
          </div>
        </div>
      </div>
    </m.div>
  );
};
