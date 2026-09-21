import React from 'react';
import { Navigate } from 'react-router-dom';
import { useUser } from '@clerk/clerk-react';
import { useAuth } from '../context/AuthContext';

export const ProtectedRoute = ({ children }) => {
  const { isAuthenticated } = useAuth();
  const { isLoaded, isSignedIn, user: clerkUser } = useUser();

  if (isAuthenticated) {
    if (clerkUser) {
      const createdTime = clerkUser.createdAt ? new Date(clerkUser.createdAt).getTime() : 0;
      const isRecentlyCreated = (Date.now() - createdTime) < 180000;
      const enrollmentStatus = sessionStorage.getItem(`face_enrolled_${clerkUser.id}`);
      if (isRecentlyCreated && !enrollmentStatus) {
        return <Navigate to="/register-face" replace />;
      }
    }
    return children;
  }

  if (!isLoaded) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-sm text-slate-400">
        Loading...
      </div>
    );
  }

  if (isSignedIn) {
    if (clerkUser) {
      const createdTime = clerkUser.createdAt ? new Date(clerkUser.createdAt).getTime() : 0;
      const isRecentlyCreated = (Date.now() - createdTime) < 180000;
      const enrollmentStatus = sessionStorage.getItem(`face_enrolled_${clerkUser.id}`);
      if (isRecentlyCreated && !enrollmentStatus) {
        return <Navigate to="/register-face" replace />;
      }
    }
    return children;
  }

  return <Navigate to="/" replace />;
};
