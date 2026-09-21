import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AnimatePresence } from 'motion/react';
import { useAuth as useClerkAuth, useUser } from '@clerk/clerk-react';
import { AlertTriangle } from 'lucide-react';
import { useAuth as useLegacyAuth } from './context/AuthContext';
import { AuthProvider } from './context/AuthProvider';
import { ProtectedRoute } from './components/ProtectedRoute';
import { LoginChoice } from './pages/LoginChoice';
import { FaceLogin } from './pages/FaceLogin';
import { ChatPage } from './pages/ChatPage';
import { ClerkSignIn } from './pages/ClerkSignIn';
import { ClerkSignUp } from './pages/ClerkSignUp';
import { RegisterFace } from './pages/RegisterFace';
import { AddFace } from './pages/AddFace';
import { PasswordLogin } from './pages/PasswordLogin';
import { Register } from './pages/Register';
import { verifyModelFilesExist } from './services/faceService';
import { setClerkTokenGetter } from './services/api';

function LoadingScreen() {
  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center text-sm text-slate-400">
      Loading...
    </div>
  );
}

function ClerkProtectedRegisterFace() {
  const { isLoaded, isSignedIn } = useUser();
  if (!isLoaded) return <LoadingScreen />;
  if (!isSignedIn) return <Navigate to="/sign-in" replace />;
  return <RegisterFace />;
}

function ClerkProtectedAddFace() {
  const { isLoaded, isSignedIn } = useUser();
  const { isAuthenticated } = useLegacyAuth();
  if (!isLoaded && !isAuthenticated) return <LoadingScreen />;
  if (!isSignedIn && !isAuthenticated) return <Navigate to="/sign-in" replace />;
  return <AddFace />;
}

function ClerkAuthBridge() {
  const { isLoaded, isSignedIn, user: clerkUser } = useUser();
  const { login, logout, loginMethod } = useLegacyAuth();

  useEffect(() => {
    if (!isLoaded) return;
    if (isSignedIn && clerkUser) {
      const username = clerkUser.username || clerkUser.primaryEmailAddress?.emailAddress || clerkUser.id;
      const currentMethod = sessionStorage.getItem('rag_login_method') || loginMethod;
      login(username, currentMethod === 'face' ? 'face' : 'clerk');
    }
  }, [isLoaded, isSignedIn, clerkUser, loginMethod, login]);

  return null;
}

function AnimatedRoutes() {
  const location = useLocation();
  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={<LoginChoice />} />
        <Route path="/login/face" element={<FaceLogin />} />
        <Route path="/login/password" element={<PasswordLogin />} />
        <Route path="/register" element={<Register />} />
        <Route path="/sign-in/*" element={<ClerkSignIn />} />
        <Route path="/sign-up/*" element={<ClerkSignUp />} />
        <Route path="/register-face" element={<ClerkProtectedRegisterFace />} />
        <Route path="/account/add-face" element={<ClerkProtectedAddFace />} />
        <Route path="/add-face" element={<Navigate to="/account/add-face" replace />} />
        <Route
          path="/chat"
          element={
            <ProtectedRoute>
              <ChatPage />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AnimatePresence>
  );
}

export function App() {
  const { getToken } = useClerkAuth();
  const [modelsMissing, setModelsMissing] = useState(false);

  useEffect(() => {
    setClerkTokenGetter(getToken);
  }, [getToken]);

  useEffect(() => {
    // Startup safety net check: verify face recognition model files in /public/models
    verifyModelFilesExist().then((exists) => {
      if (!exists) {
        setModelsMissing(true);
      }
    });
  }, []);

  return (
    <AuthProvider>
      <ClerkAuthBridge />
      <Router>
        {modelsMissing && (
          <div className="bg-amber-600 text-white text-xs px-4 py-2.5 flex items-center justify-center gap-2 text-center sticky top-0 z-50 shadow-lg">
            <AlertTriangle className="w-4 h-4 shrink-0 text-amber-200" />
            <span>
              <strong>Model Files Missing:</strong> Face recognition model weights were not found in <code className="bg-amber-700/60 px-1 py-0.5 rounded">/public/models</code>. Biometric authentication features may be unavailable.
            </span>
          </div>
        )}
        <AnimatedRoutes />
      </Router>
    </AuthProvider>
  );
}

export default App;
