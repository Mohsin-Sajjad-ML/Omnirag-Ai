import React from 'react';
import { ChatLayout } from '../components/ChatLayout';
import { m, useReducedMotion } from 'motion/react';

/**
 * ChatPage - Primary RAG conversation page for OmniRAG AI.
 * Renders the full chat interface with session history sidebar,
 * document selector, grounded answers, and inline document uploads.
 */
export const ChatPage = () => {
  const shouldReduceMotion = useReducedMotion();

  return (
    <m.div
      initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, scale: 1.02 }}
      transition={shouldReduceMotion ? { duration: 0 } : { duration: 0.2 }}
      className="h-screen w-full bg-transparent"
    >
      <ChatLayout />
    </m.div>
  );
};

export default ChatPage;
