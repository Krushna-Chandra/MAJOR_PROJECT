import React, { useState, useCallback } from "react";
import Cropper from "react-easy-crop";

const createImage = (url) =>
  new Promise((resolve, reject) => {
    const image = new Image();
    image.addEventListener("load", () => resolve(image));
    image.addEventListener("error", (error) => reject(error));
    image.setAttribute("crossOrigin", "anonymous");
    image.src = url;
  });

const getRadianAngle = (degreeValue) => (degreeValue * Math.PI) / 180;

const rotateSize = (width, height, rotation) => ({
  width:
    Math.abs(Math.cos(rotation) * width) +
    Math.abs(Math.sin(rotation) * height),
  height:
    Math.abs(Math.sin(rotation) * width) +
    Math.abs(Math.cos(rotation) * height),
});

const getCroppedImage = async (imageSrc, pixelCrop, rotation = 0) => {
  const image = await createImage(imageSrc);
  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");

  if (!ctx) {
    throw new Error("Canvas is not supported in this browser.");
  }

  const rotationRads = getRadianAngle(rotation);
  const { width: bBoxWidth, height: bBoxHeight } = rotateSize(
    image.width,
    image.height,
    rotationRads
  );

  canvas.width = bBoxWidth;
  canvas.height = bBoxHeight;

  ctx.translate(bBoxWidth / 2, bBoxHeight / 2);
  ctx.rotate(rotationRads);
  ctx.translate(-image.width / 2, -image.height / 2);
  ctx.drawImage(image, 0, 0);

  const croppedCanvas = document.createElement("canvas");
  const croppedContext = croppedCanvas.getContext("2d");

  if (!croppedContext) {
    throw new Error("Canvas is not supported in this browser.");
  }

  croppedCanvas.width = pixelCrop.width;
  croppedCanvas.height = pixelCrop.height;

  croppedContext.drawImage(
    canvas,
    pixelCrop.x,
    pixelCrop.y,
    pixelCrop.width,
    pixelCrop.height,
    0,
    0,
    pixelCrop.width,
    pixelCrop.height
  );

  const outputType = imageSrc.startsWith("data:image/png") ? "image/png" : "image/jpeg";
  return croppedCanvas.toDataURL(outputType, 0.92);
};


const ImageCropModal = ({ image, onClose, onSave }) => {
  const [crop, setCrop] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [rotation, setRotation] = useState(0);
  const cropSize = { width: 240, height: 240 };
  const [croppedAreaPixels, setCroppedAreaPixels] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const onCropComplete = useCallback((_, pixels) => {
    setCroppedAreaPixels(pixels);
  }, []);

  const handleSave = async () => {
    if (!croppedAreaPixels) return;

    try {
      setSaving(true);
      setError("");
      const croppedImage = await getCroppedImage(image, croppedAreaPixels, rotation);
      await onSave(croppedImage);
    } catch (saveError) {
      setError(saveError?.message || "Unable to process this image right now.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-content profile-editor-modal"
        onClick={(event) => event.stopPropagation()}
      >
        <button
          type="button"
          className="modal-close-btn"
          onClick={onClose}
          aria-label="Close image editor"
        >
          ×
        </button>
        <div className="profile-editor-modal__header">
          <p className="profile-editor-modal__eyebrow">Profile image editor</p>
          <h3>Edit Profile Image</h3>
          <p className="profile-editor-modal__subtext">
            Crop the frame and rotate the image until it looks right.
          </p>
        </div>
        <div className="profile-editor-modal__crop-shell">
          <Cropper
            image={image}
            crop={crop}
            zoom={zoom}
            rotation={rotation}
            aspect={1}
            cropSize={cropSize}
            cropShape="round"
            showGrid={false}
            minZoom={0.5}
            maxZoom={4}
            zoomSpeed={0.5}
            restrictPosition={false}
            onCropChange={setCrop}
            onZoomChange={setZoom}
            onRotationChange={setRotation}
            onCropComplete={onCropComplete}
          />
        </div>

        <div className="profile-editor-modal__controls">
          <label className="profile-editor-modal__control">
            <span className="profile-editor-modal__control-label">
              Zoom
              <strong>{zoom.toFixed(2)}x</strong>
            </span>
            <input
              type="range"
              min={0.5}
              max={4}
              step={0.05}
              value={zoom}
              onChange={(e) => setZoom(Number(e.target.value))}
              className="profile-editor-modal__range"
            />
          </label>
          <label className="profile-editor-modal__control">
            <span className="profile-editor-modal__control-label">
              Rotate
              <strong>{rotation}°</strong>
            </span>
            <input
              type="range"
              min={0}
              max={360}
              value={rotation}
              onChange={(e) => setRotation(Number(e.target.value))}
              className="profile-editor-modal__range"
            />
          </label>
        </div>

        {error ? <div className="profile-editor-modal__error">{error}</div> : null}

        <div className="profile-editor-modal__actions">
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
            className="profile-editor-modal__btn profile-editor-modal__btn--ghost"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving || !croppedAreaPixels}
            className="profile-editor-modal__btn profile-editor-modal__btn--primary"
          >
            {saving ? "Saving..." : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ImageCropModal;
