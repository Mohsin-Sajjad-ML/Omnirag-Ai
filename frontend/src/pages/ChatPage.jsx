import React from 'react';
import { ChatLayout } from '../components/ChatLayout';

/**
 * ChatPage - Primary RAG conversation page for OmniRAG AI.
 * Renders the full chat interface with session history sidebar,
 * document selector, grounded answers, and inline document uploads.
 */
export const ChatPage = () => {
  return <ChatLayout />;
};

export default ChatPage;
