import React, { useEffect, useState } from "react";

const computeOverlayStyle = (video, faceBox) => {
  if (!video || !faceBox || !video.videoWidth || !video.videoHeight) return null;

  const displayWidth = video.clientWidth || video.getBoundingClientRect().width;
  const displayHeight = video.clientHeight || video.getBoundingClientRect().height;
  if (!displayWidth || !displayHeight) return null;

  const scale = Math.max(displayWidth / video.videoWidth, displayHeight / video.videoHeight);
  const renderedWidth = video.videoWidth * scale;
  const renderedHeight = video.videoHeight * scale;
  const cropX = (renderedWidth - displayWidth) / 2;
  const cropY = (renderedHeight - displayHeight) / 2;

  return {
    left: `${faceBox.x * scale - cropX}px`,
    top: `${faceBox.y * scale - cropY}px`,
    width: `${faceBox.width * scale}px`,
    height: `${faceBox.height * scale}px`,
  };
};

function FaceTrackingOverlay({ videoRef, faceBox, active, compact = false }) {
  const [style, setStyle] = useState(null);

  useEffect(() => {
    const update = () => {
      setStyle(computeOverlayStyle(videoRef.current, active ? faceBox : null));
    };

    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, [active, faceBox, videoRef]);

  if (!active || !style) return null;

  return (
    <div className={`face-tracking-head-box ${compact ? "is-compact" : ""}`} style={style}>
      <span>Face</span>
    </div>
  );
}

export default FaceTrackingOverlay;
