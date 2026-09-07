import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AlertTriangle } from 'lucide-react';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { LoginChoice } from './pages/LoginChoice';
import { PasswordLogin } from './pages/PasswordLogin';
import { FaceLogin } from './pages/FaceLogin';
import { Register } from './pages/Register';
import { ChatPage } from './pages/ChatPage';
import { AddFace } from './pages/AddFace';
import { verifyModelFilesExist } from './services/faceService';

export function App() {
  const [modelsMissing, setModelsMissing] = useState(false);

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
      <Router>
        {modelsMissing && (
          <div className="bg-amber-600 text-white text-xs px-4 py-2.5 flex items-center justify-center gap-2 text-center sticky top-0 z-50 shadow-lg">
            <AlertTriangle className="w-4 h-4 shrink-0 text-amber-200" />
            <span>
              <strong>Model Files Missing:</strong> Face recognition model weights were not found in <code className="bg-amber-700/60 px-1 py-0.5 rounded">/public/models</code>. Biometric authentication features may be unavailable.
            </span>
          </div>
        )}
        <Routes>
          <Route path="/" element={<LoginChoice />} />
          <Route path="/login/password" element={<PasswordLogin />} />
          <Route path="/login/face" element={<FaceLogin />} />
          <Route path="/register" element={<Register />} />
          <Route
            path="/chat"
            element={
              <ProtectedRoute>
                <ChatPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/account/add-face"
            element={
              <ProtectedRoute>
                <AddFace />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
