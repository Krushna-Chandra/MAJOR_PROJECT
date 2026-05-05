import { useEffect, useMemo, useRef, useState } from "react";
import { FaceDetector, FilesetResolver } from "@mediapipe/tasks-vision";

const MEDIAPIPE_VERSION = "0.10.35";
const VISION_WASM_URL = `https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@${MEDIAPIPE_VERSION}/wasm`;
const FACE_MODEL_URL =
  "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/latest/blaze_face_short_range.tflite";

const DEFAULT_OPTIONS = {
  cameraOffGraceMs: 800,
  faceMissingGraceMs: 1600,
  outOfFrameGraceMs: 1400,
  detectionIntervalMs: 180,
  minFaceAreaRatio: 0.025,
  maxFaceAreaRatio: 0.72,
  edgeMarginRatio: 0.08,
  minDetectionConfidence: 0.5,
};
const EMPTY_OPTIONS = {};

const now = () => (typeof performance !== "undefined" ? performance.now() : Date.now());

const getVideoStream = (video) => {
  const stream = video?.srcObject;
  return stream instanceof MediaStream ? stream : null;
};

const isVideoTrackLive = (video) => {
  const stream = getVideoStream(video);
  if (!stream) return false;
  const tracks = stream.getVideoTracks();
  if (!tracks.length) return false;
  return tracks.some((track) => track.readyState === "live" && track.enabled && !track.muted);
};

const hasVisibleVideo = (video) =>
  Boolean(
    video &&
      video.readyState >= 2 &&
      video.videoWidth > 0 &&
      video.videoHeight > 0 &&
      !video.paused &&
      !video.ended
  );

const getFaceBox = (detection) => {
  const box = detection?.boundingBox;
  if (!box) return null;
  const x = Number(box.originX ?? box.x ?? box.xCenter - box.width / 2);
  const y = Number(box.originY ?? box.y ?? box.yCenter - box.height / 2);
  const width = Number(box.width);
  const height = Number(box.height);
  if (![x, y, width, height].every(Number.isFinite) || width <= 0 || height <= 0) return null;
  return { x, y, width, height };
};

const isFaceInsideFrame = (box, video, options) => {
  if (!box || !video?.videoWidth || !video?.videoHeight) return false;

  const frameWidth = video.videoWidth;
  const frameHeight = video.videoHeight;
  const marginX = frameWidth * options.edgeMarginRatio;
  const marginY = frameHeight * options.edgeMarginRatio;
  const areaRatio = (box.width * box.height) / (frameWidth * frameHeight);

  const insideSafeEdges =
    box.x >= marginX &&
    box.y >= marginY &&
    box.x + box.width <= frameWidth - marginX &&
    box.y + box.height <= frameHeight - marginY;

  return insideSafeEdges && areaRatio >= options.minFaceAreaRatio && areaRatio <= options.maxFaceAreaRatio;
};

const createMediaPipeDetector = async (options) => {
  const vision = await FilesetResolver.forVisionTasks(VISION_WASM_URL);
  const detectorOptions = (delegate) => ({
    baseOptions: {
      modelAssetPath: FACE_MODEL_URL,
      delegate,
    },
    runningMode: "VIDEO",
    minDetectionConfidence: options.minDetectionConfidence,
  });
  let detector;

  try {
    detector = await FaceDetector.createFromOptions(vision, detectorOptions("GPU"));
  } catch {
    detector = await FaceDetector.createFromOptions(vision, detectorOptions("CPU"));
  }

  return {
    type: "mediapipe",
    detect: (video) => detector.detectForVideo(video, now()).detections || [],
    close: () => detector.close?.(),
  };
};

const createNativeDetector = async () => {
  if (typeof window === "undefined" || typeof window.FaceDetector !== "function") {
    throw new Error("Face detection is not supported in this browser.");
  }

  const detector = new window.FaceDetector({ fastMode: true, maxDetectedFaces: 1 });
  return {
    type: "native",
    detect: async (video) => detector.detect(video),
    close: () => {},
  };
};

const initialState = {
  detectorReady: false,
  detectorType: "",
  detectorError: "",
  cameraOn: false,
  faceDetected: false,
  faceInsideFrame: false,
  stable: false,
  warning: "Camera verification has not started.",
  faceBox: null,
};

export function useFaceTracking(videoRef, { enabled = true, mode = "permission", options = EMPTY_OPTIONS } = {}) {
  const mergedOptions = useMemo(() => ({ ...DEFAULT_OPTIONS, ...options }), [options]);
  const [state, setState] = useState(initialState);
  const detectorRef = useRef(null);
  const lastCameraOnRef = useRef(0);
  const lastFaceDetectedRef = useRef(0);
  const lastFaceInsideRef = useRef(0);
  const lastDetectorRunRef = useRef(0);

  useEffect(() => {
    let cancelled = false;

    if (!enabled) {
      setState(initialState);
      return undefined;
    }

    setState((previous) => ({
      ...previous,
      detectorReady: false,
      detectorError: "",
      warning: "Loading face tracking...",
    }));

    const load = async () => {
      try {
        detectorRef.current = await createMediaPipeDetector(mergedOptions);
      } catch (mediaPipeError) {
        try {
          detectorRef.current = await createNativeDetector();
        } catch {
          if (!cancelled) {
            setState((previous) => ({
              ...previous,
              detectorReady: false,
              detectorError: mediaPipeError?.message || "Face tracking could not start.",
              warning: "Face tracking model could not load.",
            }));
          }
          return;
        }
      }

      if (!cancelled) {
        setState((previous) => ({
          ...previous,
          detectorReady: true,
          detectorType: detectorRef.current?.type || "",
          detectorError: "",
          warning: "Keep your face centered in the preview.",
        }));
      }
    };

    void load();

    return () => {
      cancelled = true;
      detectorRef.current?.close?.();
      detectorRef.current = null;
    };
  }, [enabled, mergedOptions]);

  useEffect(() => {
    if (!enabled) return undefined;

    let timerId = 0;
    let cancelled = false;

    const loop = async () => {
      if (cancelled) return;

      const video = videoRef.current;
      const currentTime = now();
      const liveCamera = isVideoTrackLive(video) && hasVisibleVideo(video);
      if (liveCamera) lastCameraOnRef.current = currentTime;

      let rawFaceDetected = false;
      let rawFaceInsideFrame = false;
      let faceBox = null;

      const canRunDetector =
        liveCamera &&
        detectorRef.current &&
        currentTime - lastDetectorRunRef.current >= mergedOptions.detectionIntervalMs;

      if (canRunDetector) {
        lastDetectorRunRef.current = currentTime;
        try {
          const detections = await detectorRef.current.detect(video);
          faceBox = getFaceBox(detections?.[0]);
          rawFaceDetected = Boolean(faceBox);
          rawFaceInsideFrame = rawFaceDetected && isFaceInsideFrame(faceBox, video, mergedOptions);
        } catch {
          rawFaceDetected = false;
          rawFaceInsideFrame = false;
        }
      }

      if (rawFaceDetected) lastFaceDetectedRef.current = currentTime;
      if (rawFaceInsideFrame) lastFaceInsideRef.current = currentTime;
      if (cancelled) return;

      const cameraOn = currentTime - lastCameraOnRef.current <= mergedOptions.cameraOffGraceMs;
      const faceDetected = currentTime - lastFaceDetectedRef.current <= mergedOptions.faceMissingGraceMs;
      const faceInsideFrame = currentTime - lastFaceInsideRef.current <= mergedOptions.outOfFrameGraceMs;

      let warning = "Camera and face position look good.";
      if (!cameraOn) {
        warning = "Camera is off or the video feed stopped.";
      } else if (!detectorRef.current) {
        warning = "Loading face tracking...";
      } else if (!faceDetected) {
        warning = "Face not detected. Please stay visible in the camera.";
      } else if (!faceInsideFrame) {
        warning = "Please keep your face centered inside the frame.";
      }

      setState((previous) => ({
        ...previous,
        cameraOn,
        faceDetected,
        faceInsideFrame,
        stable: cameraOn && faceDetected && faceInsideFrame,
        warning,
        faceBox: faceBox || previous.faceBox,
      }));

      timerId = window.setTimeout(loop, mergedOptions.detectionIntervalMs);
    };

    void loop();

    return () => {
      cancelled = true;
      window.clearTimeout(timerId);
    };
  }, [enabled, mergedOptions, videoRef]);

  return {
    ...state,
    mode,
  };
}
