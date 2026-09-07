import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Camera, KeyRound, UserPlus } from 'lucide-react';
import { BrandHeader } from '../components/BrandHeader';

export const LoginChoice = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-slate-800/80 backdrop-blur-xl border border-slate-700/60 rounded-3xl p-8 shadow-2xl shadow-slate-950/50">
        <BrandHeader subtitle="Select your preferred authentication method to continue" />

        <div className="space-y-4">
          <button
            onClick={() => navigate('/login/face')}
            className="w-full group relative flex items-center justify-between p-4 rounded-2xl bg-slate-900/60 hover:bg-indigo-950/40 border border-slate-700/60 hover:border-indigo-500/50 transition-all duration-200 text-left focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
          >
            <div className="flex items-center space-x-4">
              <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 group-hover:bg-indigo-500 group-hover:text-white transition-all">
                <Camera className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-base font-semibold text-slate-100 group-hover:text-indigo-300 transition-colors">
                  Login with Face
                </h3>
                <p className="text-xs text-slate-400">Quick biometric passwordless sign in</p>
              </div>
            </div>
            <span className="text-xs font-medium text-indigo-400 bg-indigo-500/10 px-2.5 py-1 rounded-full border border-indigo-500/20">
              Biometric
            </span>
          </button>

          <button
            onClick={() => navigate('/login/password')}
            className="w-full group relative flex items-center justify-between p-4 rounded-2xl bg-slate-900/60 hover:bg-indigo-950/40 border border-slate-700/60 hover:border-indigo-500/50 transition-all duration-200 text-left focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
          >
            <div className="flex items-center space-x-4">
              <div className="w-12 h-12 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 group-hover:bg-indigo-500 group-hover:text-white transition-all">
                <KeyRound className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-base font-semibold text-slate-100 group-hover:text-indigo-300 transition-colors">
                  Login with Password
                </h3>
                <p className="text-xs text-slate-400">Sign in with username & password</p>
              </div>
            </div>
          </button>
        </div>

        <div className="mt-8 pt-6 border-t border-slate-700/50 text-center">
          <p className="text-sm text-slate-400">
            Don't have an account?{' '}
            <Link
              to="/register"
              className="font-medium text-indigo-400 hover:text-indigo-300 hover:underline inline-flex items-center gap-1 transition-colors"
            >
              <UserPlus className="w-4 h-4" />
              Register
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};
