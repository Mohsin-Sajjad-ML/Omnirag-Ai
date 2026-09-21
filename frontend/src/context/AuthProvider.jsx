import React, { useState, useCallback } from 'react';
import { AuthContext } from './AuthContext';

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    // Persist login state in session storage so page refreshes maintain auth state
    return sessionStorage.getItem('rag_user') || null;
  });

  const [loginMethod, setLoginMethod] = useState(() => {
    // Persist login method ('face' | 'password') across page refreshes
    return sessionStorage.getItem('rag_login_method') || 'password';
  });

  const login = useCallback((username, method = 'password') => {
    setUser(username);
    setLoginMethod(method);
    sessionStorage.setItem('rag_user', username);
    sessionStorage.setItem('rag_login_method', method);
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    setLoginMethod(null);
    sessionStorage.removeItem('rag_user');
    sessionStorage.removeItem('rag_login_method');
  }, []);

  return (
    <AuthContext.Provider value={{ user, loginMethod, login, logout, isAuthenticated: !!user }}>
      {children}
    </AuthContext.Provider>
  );
};
