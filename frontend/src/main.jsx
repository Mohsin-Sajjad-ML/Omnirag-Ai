import { ClerkProvider } from '@clerk/clerk-react';
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import { LazyMotion, domAnimation, MotionConfig } from 'motion/react'

const publishableKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

if (!publishableKey) {
  throw new Error('Missing VITE_CLERK_PUBLISHABLE_KEY. Run `clerk env pull` in frontend.');
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <LazyMotion features={domAnimation}>
      <MotionConfig transition={{ type: 'spring', bounce: 0.1 }}>
        <ClerkProvider 
          publishableKey={publishableKey} 
          afterSignOutUrl="/"
          appearance={{
            variables: {
              colorPrimary: '#4f46e5',
              colorBackground: 'rgba(15, 23, 42, 0.0)',
              colorInputBackground: 'rgba(15, 23, 42, 0.5)',
              colorInputText: '#f1f5f9',
              colorText: '#f1f5f9',
              colorTextSecondary: '#94a3b8',
              borderRadius: '0.75rem',
            },
            elements: {
              card: 'glass-panel border-none shadow-none bg-transparent',
              formButtonPrimary: 'bg-indigo-600 hover:bg-indigo-500 shadow-lg shadow-indigo-600/30 transition-all',
              headerTitle: 'text-slate-100 font-bold',
              headerSubtitle: 'text-slate-400 text-xs',
              socialButtonsBlockButton: 'bg-slate-900/80 border border-slate-700 hover:bg-slate-800 text-slate-300 transition-all',
              socialButtonsBlockButtonText: 'text-slate-300',
              dividerLine: 'bg-slate-700/50',
              dividerText: 'text-slate-500 text-xs',
              formFieldLabel: 'text-slate-300 text-xs font-medium uppercase tracking-wider',
              formFieldInput: 'bg-slate-900/80 border-slate-700 text-slate-100 placeholder-slate-500 focus:border-indigo-500 focus:ring-indigo-500 transition-all text-sm rounded-xl',
              footerActionText: 'text-slate-400',
              footerActionLink: 'text-indigo-400 hover:text-indigo-300',
              identityPreviewText: 'text-slate-300',
              identityPreviewEditButtonIcon: 'text-indigo-400',
            }
          }}
        >
          <App />
        </ClerkProvider>
      </MotionConfig>
    </LazyMotion>
  </React.StrictMode>,
)