import React from 'react';
import { SignUp } from '@clerk/clerk-react';
import { ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';
import { m, useReducedMotion } from 'motion/react';

export const ClerkSignUp = () => {
  const shouldReduceMotion = useReducedMotion();
  return (
    <m.div
      initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      exit={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: -15 }}
      transition={{ duration: 0.3 }}
      className="auth-page min-h-screen flex flex-col items-center justify-center p-4"
    >
      <div className="w-full max-w-md mb-3">
        <Link
          to="/"
          className="inline-flex items-center text-xs font-medium text-slate-400 hover:text-slate-200 transition-colors"
        >
          <ArrowLeft className="w-4 h-4 mr-1.5" /> Back to login options
        </Link>
      </div>
      <SignUp
        routing="path"
        path="/sign-up"
        signInUrl="/sign-in"
        forceRedirectUrl="/register-face"
        fallbackRedirectUrl="/register-face"
        appearance={{
          elements: {
            rootBox: 'w-full max-w-md',
            card: 'glass-panel bg-[rgba(18,16,31,0.72)] backdrop-blur-2xl border border-white/10 rounded-3xl shadow-2xl shadow-black/80',
            headerTitle: 'text-white font-bold text-xl tracking-tight',
            headerSubtitle: 'text-slate-400 text-xs mt-1',
            formButtonPrimary:
              'bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 text-white font-semibold text-xs sm:text-sm rounded-xl py-2.5 shadow-md shadow-violet-600/30 transition-all active:scale-[0.98]',
            formFieldInput:
              'bg-white/5 border border-white/10 rounded-xl text-slate-100 text-xs sm:text-sm focus:border-violet-500 focus:ring-1 focus:ring-violet-500/40 placeholder-slate-500 transition-colors',
            formFieldLabel: 'text-slate-300 text-xs font-medium uppercase tracking-wider',
            footerActionLink: 'text-violet-400 hover:text-fuchsia-300 font-medium transition-colors',
            footerActionText: 'text-slate-400 text-xs',
            socialButtonsBlockButton:
              'glass-panel bg-white/10 hover:bg-white/20 border border-violet-500/30 hover:border-fuchsia-500/60 text-white rounded-xl shadow-lg shadow-black/40 hover:shadow-violet-500/25 transition-all active:scale-[0.98]',
            socialButtonsIconButton:
              'glass-panel bg-white/10 hover:bg-white/20 border border-violet-500/30 hover:border-fuchsia-500/60 text-white rounded-xl shadow-lg shadow-black/40 hover:shadow-violet-500/25 transition-all active:scale-[0.98]',
            socialButtonsBlockButtonText: 'text-white font-medium text-xs',
            otpCodeField: 'gap-2.5 justify-center',
            otpCodeFieldInputs: 'gap-2.5 justify-center',
            otpCodeFieldInput:
              'bg-[#1c1632] border-2 border-violet-500/50 hover:border-fuchsia-500/70 focus:border-fuchsia-500 rounded-xl text-white text-lg font-bold shadow-[0_0_16px_rgba(139,92,246,0.35)] focus:shadow-[0_0_24px_rgba(217,70,239,0.7)] transition-all text-center',
            formResendCodeLink: 'text-violet-400 hover:text-fuchsia-300 font-semibold underline underline-offset-2',
            dividerLine: 'bg-white/10',
            dividerText: 'text-slate-500 text-[10px] uppercase tracking-widest font-semibold',
            footer: 'bg-transparent border-t border-white/10 pt-4',
          },
          variables: {
            colorPrimary: '#8b5cf6',
            colorBackground: 'rgba(18, 16, 31, 0.72)',
            colorInputBackground: 'rgba(255, 255, 255, 0.05)',
            colorInputBorder: 'rgba(255, 255, 255, 0.1)',
            colorText: '#f3f4f6',
            colorTextSecondary: '#94a3b8',
            borderRadius: '1rem',
            fontFamily: "'Plus Jakarta Sans', 'Segoe UI', sans-serif",
          },
        }}
      />
    </m.div>
  );
};
