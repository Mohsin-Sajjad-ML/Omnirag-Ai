import React, { useEffect, useRef, useState } from 'react';
import { Camera, AlertCircle, Loader2, CheckCircle2, Users, EyeOff } from 'lucide-react';
import { m, AnimatePresence, useReducedMotion } from 'motion/react';
import {
  loadFaceModels,
  extractFaceDescriptorFromVideo,
  countFacesInVideo,
} from '../services/faceService';

/**
 * Enhanced FaceCapture Component
 *
 * Features:
 * 1. Loads face-api.js neural network models from /models.
 * 2. Requests camera permissions and binds live MediaStream to <video>.
 * 3. Continuous real-time face detection every ~350ms (non-blocking).
 * 4. Real-time status indicator:
 *    - Red: "No face detected"
 *    - Green: "Face detected, ready to capture"
 *    - Yellow: "Multiple faces detected, please ensure only one person is visible"
 * 5. Disables "Capture" button unless exactly ONE face is detected.
 * 6. Full cleanup of timers and camera tracks on unmount.
 * 7. Post-capture safety net validation preserved.
 */
export const FaceCapture = ({
  onCapture,
  buttonText = 'Capture Face',
  isProcessing = false,
  disabled = false,
}) => {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const shouldReduceMotion = useReducedMotion();

  const [loadingModels, setLoadingModels] = useState(true);
  const [modelError, setModelError] = useState('');
  const [cameraError, setCameraError] = useState('');
  const [detectionError, setDetectionError] = useState('');
  const [isCapturing, setIsCapturing] = useState(false);
  const [cameraReady, setCameraReady] = useState(false);
  const [cameraRetryKey, setCameraRetryKey] = useState(0);

  // Real-time detection state: 'scanning' | 'no_face' | 'face_detected' | 'multiple_faces'
  const [detectionState, setDetectionState] = useState('scanning');

  // ---------------------------------------------------------------------------
  // 1. Initialize models and camera stream on mount
  // ---------------------------------------------------------------------------
  useEffect(() => {
    let isMounted = true;

    async function initialize() {
      // Load Neural Network Models
      try {
        setLoadingModels(true);
        setModelError('');
        await loadFaceModels();
      } catch (err) {
        if (!isMounted) return;
        console.error('Model loading failure:', err);
        setModelError(
          err.message ||
            'Failed to load facial recognition models. Please ensure model weight files exist in /public/models.'
        );
        setLoadingModels(false);
        return;
      }

      if (!isMounted) return;
      setLoadingModels(false);

      // Request webcam stream. A minimal fallback helps browsers that reject
      // ideal resolution/facingMode constraints while the camera is available.
      try {
        setCameraError('');
        let stream;
        try {
          stream = await navigator.mediaDevices.getUserMedia({
            video: {
              width: { ideal: 640 },
              height: { ideal: 480 },
              facingMode: 'user',
            },
            audio: false,
          });
        } catch (firstError) {
          if (firstError.name === 'NotReadableError' || firstError.name === 'OverconstrainedError') {
            stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
          } else {
            throw firstError;
          }
        }

        if (!isMounted) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }

        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.onloadedmetadata = () => {
            if (isMounted) {
              videoRef.current.play().catch((e) => console.warn('Video play interrupted:', e));
              setCameraReady(true);
            }
          };
        }
      } catch (err) {
        if (!isMounted) return;
        console.error('Camera access error:', err);
        if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
          setCameraError(
            'Camera access was denied. Please allow camera permissions in your browser to proceed.'
          );
        } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
          setCameraError('No camera found on your device. Please connect a webcam.');
        } else if (err.name === 'NotReadableError') {
          setCameraError('The camera is busy or unavailable. Close other camera apps or browser tabs, then click Try Camera Again.');
        } else {
          setCameraError('Unable to access camera: ' + (err.message || 'Unknown error'));
        }
      }
    }

    initialize();

    // Cleanup camera tracks on unmount
    return () => {
      isMounted = false;
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      }
    };
  }, [cameraRetryKey]);

  // ---------------------------------------------------------------------------
  // 2. Continuous real-time face detection loop (every 350ms)
  // ---------------------------------------------------------------------------
  useEffect(() => {
    // Only detect when camera is streaming, models are loaded, and not actively capturing/processing
    if (!cameraReady || loadingModels || isCapturing || isProcessing) {
      return;
    }

    let isMounted = true;
    let timerId = null;

    const detectLoop = async () => {
      if (!isMounted || !videoRef.current) return;

      try {
        const faceCount = await countFacesInVideo(videoRef.current);
        if (isMounted && faceCount !== null) {
          if (faceCount === 0) {
            setDetectionState('no_face');
          } else if (faceCount === 1) {
            setDetectionState('face_detected');
          } else {
            setDetectionState('multiple_faces');
          }
        }
      } catch (err) {
        console.debug('Continuous detection error:', err);
      }

      // Schedule next detection pass after 350ms to maintain optimal CPU & browser performance
      if (isMounted) {
        timerId = setTimeout(detectLoop, 350);
      }
    };

    // Begin loop
    timerId = setTimeout(detectLoop, 150);

    // Guaranteed unmount cleanup to avoid background execution
    return () => {
      isMounted = false;
      if (timerId) {
        clearTimeout(timerId);
        timerId = null;
      }
    };
  }, [cameraReady, loadingModels, isCapturing, isProcessing]);

  // ---------------------------------------------------------------------------
  // 3. Handle Capture with Post-Capture Safety Net
  // ---------------------------------------------------------------------------
  const handleCapture = async () => {
    if (
      !videoRef.current ||
      isCapturing ||
      isProcessing ||
      disabled ||
      detectionState !== 'face_detected'
    ) {
      return;
    }

    setDetectionError('');
    setIsCapturing(true);

    try {
      // Full 128D descriptor extraction with double-check validation
      const result = await extractFaceDescriptorFromVideo(videoRef.current);

      // Post-capture safety net: check if face state changed at moment of capture
      if (result.error) {
        setDetectionError(result.error);
        setIsCapturing(false);
        return;
      }

      if (result.descriptor && result.descriptor.length === 128) {
        onCapture(result.descriptor);
      } else {
        setDetectionError('Unable to extract valid face descriptor. Please reposition and try again.');
      }
    } catch (err) {
      console.error('Face capture error:', err);
      setDetectionError('An error occurred during facial extraction. Please try again.');
    } finally {
      setIsCapturing(false);
    }
  };

  // Button enable condition: exactly one face detected, ready, not busy
  const canCapture =
    cameraReady &&
    !loadingModels &&
    !modelError &&
    !cameraError &&
    !isCapturing &&
    !isProcessing &&
    !disabled &&
    detectionState === 'face_detected';

  // Dynamic visual indicators based on continuous detection state
  const getIndicatorDetails = () => {
    switch (detectionState) {
      case 'face_detected':
        return {
          dotClass: 'bg-emerald-400 animate-pulse',
          badgeClass: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300',
          text: 'Face detected, ready to capture',
          icon: <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />,
          ovalClass: 'border-emerald-400/80 shadow-[0_0_15px_rgba(52,211,153,0.3)]',
        };
      case 'multiple_faces':
        return {
          dotClass: 'bg-amber-400',
          badgeClass: 'bg-amber-500/10 border-amber-500/30 text-amber-300',
          text: 'Multiple faces detected, please ensure only one person is visible',
          icon: <Users className="w-3.5 h-3.5 text-amber-400" />,
          ovalClass: 'border-amber-400/80 shadow-[0_0_12px_rgba(251,191,36,0.3)]',
        };
      case 'no_face':
        return {
          dotClass: 'bg-rose-500',
          badgeClass: 'bg-rose-500/10 border-rose-500/30 text-rose-300',
          text: 'No face detected',
          icon: <EyeOff className="w-3.5 h-3.5 text-rose-400" />,
          ovalClass: 'border-rose-500/40',
        };
      case 'scanning':
      default:
        return {
          dotClass: 'bg-indigo-400 animate-pulse',
          badgeClass: 'bg-slate-800/80 border-slate-700/60 text-slate-300',
          text: 'Scanning for face...',
          icon: <Loader2 className="w-3.5 h-3.5 text-indigo-400 animate-spin" />,
          ovalClass: 'border-indigo-400/40',
        };
    }
  };

  const indicator = getIndicatorDetails();

  return (
    <div className="w-full flex flex-col items-center">
      {/* Model Loading State */}
      {loadingModels && (
        <div className="w-full p-8 rounded-2xl bg-slate-900/80 border border-slate-700/60 flex flex-col items-center justify-center text-center space-y-3 mb-4">
          <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
          <p className="text-sm font-medium text-slate-200">
            Loading AI facial recognition models...
          </p>
          <p className="text-xs text-slate-400">
            First-time model load from in-browser neural networks
          </p>
        </div>
      )}

      {/* Model Loading Error */}
      {modelError && (
        <div className="w-full p-4 mb-4 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start gap-3 text-rose-300 text-sm">
          <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Model Initialization Error</p>
            <p className="text-xs text-rose-300/90 mt-1">{modelError}</p>
          </div>
        </div>
      )}

      {/* Camera Access Error */}
      {cameraError && (
        <div className="w-full p-4 mb-4 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start gap-3 text-rose-300 text-sm">
          <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Webcam Not Available</p>
            <p className="text-xs text-rose-300/90 mt-1">{cameraError}</p>
            <button
              type="button"
              onClick={() => setCameraRetryKey((key) => key + 1)}
              className="mt-3 rounded-lg border border-rose-400/40 px-3 py-1.5 text-xs font-semibold text-rose-200 transition-colors hover:bg-rose-500/10"
            >
              Try Camera Again
            </button>
          </div>
        </div>
      )}

      {/* Post-Capture Safety Net Feedback Error */}
      {detectionError && (
        <div className="w-full p-3.5 mb-4 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-start gap-2.5 text-amber-300 text-xs animate-shake">
          <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div className="font-medium">{detectionError}</div>
        </div>
      )}

      {/* Live Video Preview Box */}
      {!loadingModels && !modelError && !cameraError && (
        <m.div
          initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ type: 'spring', bounce: 0, duration: 0.4 }}
          className="w-full max-w-sm flex flex-col items-center"
        >
          <m.div 
            animate={
              detectionError 
                ? (shouldReduceMotion ? { x: [-5, 5, -5, 5, 0] } : { x: [-10, 10, -10, 10, 0] })
                : {}
            }
            transition={{ duration: 0.4 }}
            className="relative w-full aspect-[4/3] rounded-2xl overflow-hidden bg-slate-950 border-2 border-slate-700/80 shadow-inner flex items-center justify-center mb-3"
          >
            <video
              ref={videoRef}
              playsInline
              muted
              className="w-full h-full object-cover scale-x-[-1]" /* Mirror view for natural camera */
            />

            {/* Dynamic oval face guide overlay reflecting real-time detection state */}
            <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
              {(isCapturing || isProcessing) && (
                <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/40 backdrop-blur-[2px] z-20">
                  {/* Glowing pulsing rings */}
                  <m.div
                    initial={shouldReduceMotion ? { opacity: 0 } : { scale: 0.92, opacity: 0.4 }}
                    animate={
                      shouldReduceMotion
                        ? { opacity: 1 }
                        : {
                            scale: [0.92, 1.1, 0.92],
                            opacity: [0.4, 0.9, 0.4],
                          }
                    }
                    transition={
                      shouldReduceMotion
                        ? { duration: 0 }
                        : { repeat: Infinity, duration: 1.4, ease: 'easeInOut' }
                    }
                    className="absolute w-44 h-56 rounded-[50%] border-4 border-violet-500 shadow-[0_0_30px_rgba(139,92,246,0.7)]"
                  />
                  <m.div
                    initial={shouldReduceMotion ? { opacity: 0 } : { scale: 0.86, opacity: 0.25 }}
                    animate={
                      shouldReduceMotion
                        ? { opacity: 1 }
                        : {
                            scale: [0.86, 1.16, 0.86],
                            opacity: [0.25, 0.7, 0.25],
                          }
                    }
                    transition={
                      shouldReduceMotion
                        ? { duration: 0 }
                        : { repeat: Infinity, duration: 1.8, ease: 'easeInOut', delay: 0.15 }
                    }
                    className="absolute w-44 h-56 rounded-[50%] border-2 border-fuchsia-400 shadow-[0_0_20px_rgba(217,70,239,0.5)]"
                  />
                  <m.div
                    initial={shouldReduceMotion ? { opacity: 0 } : { scale: 0.85, y: 8 }}
                    animate={{ scale: 1, y: 0 }}
                    transition={shouldReduceMotion ? { duration: 0 } : { type: 'spring', stiffness: 350, damping: 24 }}
                    className="glass-panel px-4 py-2 rounded-full border border-violet-400/50 text-white text-xs font-semibold flex items-center gap-2 shadow-2xl bg-violet-950/80 z-30"
                  >
                    <Loader2 className="w-3.5 h-3.5 text-fuchsia-400 animate-spin" />
                    <span>Verifying biometrics...</span>
                  </m.div>
                </div>
              )}
              <div
                className={`w-44 h-56 rounded-[50%] border-2 border-dashed transition-all duration-500 flex items-center justify-center ${
                  (isCapturing || isProcessing) ? 'border-violet-400 shadow-[0_0_20px_rgba(139,92,246,0.5)]' : indicator.ovalClass
                }`}
              >
                <span className="text-[10px] uppercase font-semibold tracking-wider text-slate-200 bg-slate-900/80 backdrop-blur-sm px-2.5 py-0.5 rounded-full border border-slate-700/60 shadow transition-opacity duration-300" style={{ opacity: (isCapturing || isProcessing) ? 0 : 1 }}>
                  Position Face
                </span>
              </div>
            </div>

            {/* Top-left camera live indicator */}
            <div className="absolute top-3 left-3 bg-slate-900/80 backdrop-blur-md px-2.5 py-1 rounded-full border border-slate-700/60 flex items-center gap-1.5 text-[11px] font-medium text-slate-300">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              Live
            </div>
          </m.div>

          {/* Real-time Detection Status Indicator with smooth color/label transition */}
          <m.div
            layout
            className={`w-full mb-4 px-3 py-2 rounded-xl border flex items-center justify-center gap-2 text-xs font-medium text-center transition-all duration-500 ${indicator.badgeClass}`}
          >
            <span className={`w-2.5 h-2.5 rounded-full shrink-0 transition-colors duration-500 ${indicator.dotClass}`}></span>
            <AnimatePresence mode="wait">
              <m.div
                key={indicator.text}
                initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: 4 }}
                transition={shouldReduceMotion ? { duration: 0 } : { duration: 0.25, ease: 'easeInOut' }}
                className="flex items-center gap-1.5 truncate"
              >
                {indicator.icon}
                <span>{indicator.text}</span>
              </m.div>
            </AnimatePresence>
          </m.div>
        </m.div>
      )}

      {/* Capture Action Button */}
      {!loadingModels && !modelError && !cameraError && (
        <button
          type="button"
          onClick={handleCapture}
          disabled={!canCapture}
          className="w-full py-3.5 px-4 rounded-xl bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 active:scale-[0.99] text-white font-semibold text-sm shadow-lg shadow-violet-600/30 transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-violet-400 cursor-pointer"
        >
          {isCapturing || isProcessing ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              <span>Verifying biometrics...</span>
            </>
          ) : (
            <>
              <Camera className="w-5 h-5" />
              <span>{buttonText}</span>
            </>
          )}
        </button>
      )}
    </div>
  );
};
