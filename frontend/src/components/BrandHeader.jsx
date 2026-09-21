import React from 'react';
import { Bot, Sparkles } from 'lucide-react';

export const BrandHeader = ({ subtitle }) => {
  return (
    <div className="flex flex-col items-center text-center mb-8">
      <div className="relative mb-3 group">
        <div className="absolute -inset-1.5 bg-gradient-to-r from-violet-600 via-fuchsia-600 to-pink-500 rounded-2xl blur-md opacity-60 group-hover:opacity-100 transition duration-500" />
        <div className="relative w-14 h-14 rounded-2xl bg-gradient-to-tr from-violet-600 via-fuchsia-600 to-pink-500 flex items-center justify-center shadow-lg shadow-violet-600/35 ring-1 ring-white/30">
          <Bot className="w-8 h-8 text-white" />
        </div>
        <div className="absolute -top-1.5 -right-1.5 bg-fuchsia-400 p-1 rounded-full text-slate-950 shadow-md">
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
