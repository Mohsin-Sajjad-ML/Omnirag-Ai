import React from 'react';
import { Bot, Sparkles } from 'lucide-react';

export const BrandHeader = ({ subtitle }) => {
  return (
    <div className="flex flex-col items-center text-center mb-8">
      <div className="relative mb-3">
        <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-purple-500 flex items-center justify-center shadow-lg shadow-indigo-500/25 ring-1 ring-white/20">
          <Bot className="w-8 h-8 text-white" />
        </div>
        <div className="absolute -top-1 -right-1 bg-amber-400 p-1 rounded-full text-slate-900 shadow">
          <Sparkles className="w-3 h-3" />
        </div>
      </div>
      <h1 className="text-2xl font-bold tracking-tight bg-gradient-to-r from-white via-slate-100 to-slate-400 bg-clip-text text-transparent">
        OmniRAG AI
      </h1>
      {subtitle && (
        <p className="text-sm text-slate-400 mt-1 max-w-xs">{subtitle}</p>
      )}
    </div>
  );
};
