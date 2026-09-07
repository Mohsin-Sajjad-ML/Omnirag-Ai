/**
 * faceService.js - Biometric model loading and face descriptor extraction service.
 *
 * Utilizes face-api.js (in-browser TensorFlow.js) to:
 * 1. Verify model weight manifest and shard assets exist in /public/models.
 * 2. Load TinyFaceDetector, FaceLandmark68Net, and FaceRecognitionNet models.
 * 3. Extract 128-dimensional facial embedding vectors from live video streams.
 */

import * as faceapi from 'face-api.js';

// Required model files downloaded in /frontend/public/models
export const REQUIRED_MODEL_FILES = [
  '/models/tiny_face_detector_model-weights_manifest.json',
  '/models/tiny_face_detector_model-shard1',
  '/models/face_landmark_68_model-weights_manifest.json',
  '/models/face_landmark_68_model-shard1',
  '/models/face_recognition_model-weights_manifest.json',
  '/models/face_recognition_model-shard1',
  '/models/face_recognition_model-shard2',
];

let modelsLoaded = false;
let modelLoadingPromise = null;

/**
 * Startup check: Verifies all 7 model files can be reached on the server.
 * Returns true if all files exist and are reachable; false if any are missing.
 */
export async function verifyModelFilesExist() {
  try {
    const checks = await Promise.all(
      REQUIRED_MODEL_FILES.map(async (fileUrl) => {
        const response = await fetch(fileUrl, { method: 'HEAD' });
        return response.ok;
      })
    );
    return checks.every(Boolean);
  } catch (error) {
    console.warn('Unable to verify model file existence via HEAD request:', error);
    // Fall back to attempting model load directly
    return true;
  }
}

/**
 * Loads the face-api.js neural network models from /models.
 * Caches the loading promise so models are only loaded once per session.
 */
export async function loadFaceModels() {
  if (modelsLoaded) {
    return true;
  }

  if (modelLoadingPromise) {
    return modelLoadingPromise;
  }

  modelLoadingPromise = (async () => {
    // Check if model files are available
    const filesExist = await verifyModelFilesExist();
    if (!filesExist) {
      throw new Error(
        'Required face recognition models are missing in /public/models. Please ensure all 7 model files are downloaded.'
      );
    }

    const MODEL_BASE_URL = '/models';

    // Load TinyFaceDetector, FaceLandmarks, and FaceRecognition models concurrently
    await Promise.all([
      faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_BASE_URL),
      faceapi.nets.faceLandmark68Net.loadFromUri(MODEL_BASE_URL),
      faceapi.nets.faceRecognitionNet.loadFromUri(MODEL_BASE_URL),
    ]);

    modelsLoaded = true;
    return true;
  })();

  try {
    return await modelLoadingPromise;
  } catch (err) {
    // Reset promise so subsequent retries can re-attempt loading
    modelLoadingPromise = null;
    throw err;
  }
}

/**
 * Checks if face-api.js neural networks are ready.
 */
export function areModelsLoaded() {
  return modelsLoaded;
}

/**
 * Performs face detection, landmark positioning, and descriptor extraction
 * on the current frame of a HTMLVideoElement.
 *
 * Enforces:
 * - 0 faces -> Error: "No face detected, please try again"
 * - >1 faces -> Error: "Please ensure only one face is visible"
 * - 1 face -> Returns 128-element float array
 *
 * @param {HTMLVideoElement} videoElement
 * @returns {Promise<{ descriptor?: number[], error?: string }>}
 */
export async function extractFaceDescriptorFromVideo(videoElement) {
  if (!videoElement || videoElement.readyState < 2) {
    return { error: 'Camera stream is not ready. Please wait a moment.' };
  }

  // Detect all faces in video frame using TinyFaceDetector
  // inputSize: 320 provides good balance of inference speed and accuracy in browser
  const detectorOptions = new faceapi.TinyFaceDetectorOptions({
    inputSize: 320,
    scoreThreshold: 0.5,
  });

  const detections = await faceapi
    .detectAllFaces(videoElement, detectorOptions)
    .withFaceLandmarks()
    .withFaceDescriptors();

  if (!detections || detections.length === 0) {
    return { error: 'No face detected, please try again' };
  }

  if (detections.length > 1) {
    return { error: 'Please ensure only one face is visible' };
  }

  // Convert Float32Array to standard JavaScript number array for JSON transmission
  const descriptorArray = Array.from(detections[0].descriptor);

  return { descriptor: descriptorArray };
}

/**
 * Lightweight real-time face counter on a live HTMLVideoElement frame.
 * Runs only the TinyFaceDetector (omits landmarks and descriptors)
 * with a compact 224px input size for fast (~15-25ms) non-blocking
 * continuous feedback every 300-500ms.
 *
 * @param {HTMLVideoElement} videoElement
 * @returns {Promise<number | null>} Number of detected faces, or null if video is not ready
 */
export async function countFacesInVideo(videoElement) {
  if (
    !videoElement ||
    videoElement.readyState < 2 ||
    videoElement.paused ||
    videoElement.ended ||
    videoElement.videoWidth === 0
  ) {
    return null;
  }

  try {
    const detectorOptions = new faceapi.TinyFaceDetectorOptions({
      inputSize: 224,
      scoreThreshold: 0.5,
    });

    const detections = await faceapi.detectAllFaces(videoElement, detectorOptions);
    return detections ? detections.length : 0;
  } catch (err) {
    console.debug('Frame face detection skipped:', err);
    return null;
  }
}

