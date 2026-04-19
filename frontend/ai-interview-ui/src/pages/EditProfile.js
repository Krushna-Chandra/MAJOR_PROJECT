import React, { useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import ImageCropModal from "../components/ImageCropModal";

function EditProfile() {
  const navigate = useNavigate();
  const token = localStorage.getItem("token");

  const storedUser = JSON.parse(localStorage.getItem("user"));

  // names start empty (explicit edit only)
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");

  // show current image
  const [profileImage, setProfileImage] = useState(
    storedUser?.profile_image || null
  );
  const [originalUploadImage, setOriginalUploadImage] = useState(null);

  const [confirmRemove, setConfirmRemove] = useState(false);
  const [loading, setLoading] = useState(false);
  const [cropModalImg, setCropModalImg] = useState(null);
  const [notification, setNotification] = useState(null);
  const [showSuccessPopup, setShowSuccessPopup] = useState(false);

  /* ---------- IMAGE UPLOAD ---------- */
  const handleImageUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onloadend = () => {
      setOriginalUploadImage(reader.result);
      setCropModalImg(reader.result);
    };
    reader.readAsDataURL(file);
  };

  /* ---------- SAVE PROFILE ---------- */
  const handleSave = async () => {
    // rule: last name alone not allowed
    if (firstName.trim() === "" && lastName.trim() !== "") {
      setNotification({ type: "error", message: "Fill out the first name first." });
      return;
    }

    // determine update intent
    let nameUpdateMode = "none";
    if (firstName.trim() !== "" && lastName.trim() === "") {
      nameUpdateMode = "first_only";
    }
    if (firstName.trim() !== "" && lastName.trim() !== "") {
      nameUpdateMode = "full";
    }

    setLoading(true);
    setNotification(null);
    try {
      const payload = {};

      if (firstName.trim() !== "") {
        payload.first_name = firstName;
      }

      if (lastName.trim() !== "") {
        payload.last_name = lastName;
      }

      // image logic
      // null -> confirmed remove
      // base64 -> update
      if (profileImage === null) {
        payload.profile_image = "";
      } else if (profileImage !== storedUser?.profile_image) {
        payload.profile_image = profileImage;
      }

      const res = await axios.put(
        "http://127.0.0.1:8000/profile",
        payload,
        {
          headers: {
            Authorization: "Bearer " + token
          }
        }
      );

      // IMPORTANT: merge + store intent
      const existingUser = JSON.parse(localStorage.getItem("user"));
      localStorage.setItem(
        "user",
        JSON.stringify({
          ...existingUser,
          ...res.data.user,
          name_update_mode: nameUpdateMode
        })
      );

      setNotification({ type: "success", message: "Profile updated successfully." });
      setShowSuccessPopup(true);
    } catch (err) {
      setNotification({
        type: "error",
        message: err.response?.data?.detail || "Profile update failed"
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card" style={{ textAlign: "center" }}>
        <h2>Edit Profile</h2>

        {notification && (
          <div className={`profile-notification profile-notification--${notification.type}`}>
            {notification.message}
          </div>
        )}

        {/* CURRENT IMAGE */}
        <div style={{ marginBottom: "20px" }}>
          {profileImage ? (
            <>
              <button
                type="button"
                className="edit-image-hover-wrapper"
                style={{
                  width: "120px",
                  height: "120px",
                  borderRadius: "50%",
                  display: "block",
                  margin: "0 auto 10px",
                  padding: 0,
                  border: "none",
                  background: "transparent",
                  overflow: "hidden",
                  cursor: "pointer",
                  position: "relative"
                }}
                onClick={() => {
                  setCropModalImg(originalUploadImage || profileImage);
                  setConfirmRemove(false);
                }}
                title="Edit profile image"
              >
                <img
                  src={profileImage}
                  alt="profile"
                  style={{
                    width: "120px",
                    height: "120px",
                    borderRadius: "50%",
                    objectFit: "cover",
                    display: "block"
                  }}
                />
                <span className="edit-image-hover-text">Edit</span>
              </button>

              {!confirmRemove ? (
                <button
                  onClick={() => setConfirmRemove(true)}
                  className="mock-btn"
                  style={{ background: "#e74c3c", marginBottom: 10 }}
                >
                  Remove Image
                </button>
              ) : (
                <div>
                  <p style={{ fontSize: "14px" }}>
                    Remove profile image?
                  </p>
                  <div style={{ display: "flex", justifyContent: "center", gap: 8 }}>
                    <button
                      onClick={() => {
                        setProfileImage(null);
                        setOriginalUploadImage(null);
                        setConfirmRemove(false);
                      }}
                      className="mock-btn"
                      style={{ background: "#e74c3c" }}
                    >
                      Yes
                    </button>
                    <button
                      onClick={() => setConfirmRemove(false)}
                      className="mock-btn"
                      style={{ background: "#ccc", color: "#000" }}
                    >
                      No
                    </button>
                  </div>
                </div>
              )}
            </>
          ) : (
            <p style={{ fontSize: "14px", color: "#666" }}>
              Default profile image
            </p>
          )}
        </div>

        <input type="file" accept="image/*" onChange={handleImageUpload} />

        <input
          placeholder="First Name"
          value={firstName}
          onChange={(e) => setFirstName(e.target.value)}
        />

        <input
          placeholder="Last Name"
          value={lastName}
          onChange={(e) => setLastName(e.target.value)}
        />

        <button
          onClick={handleSave}
          disabled={loading}
          className="mock-btn"
          style={{ width: "100%", marginTop: 12 }}
        >
          {loading ? "Saving..." : "Save Changes"}
        </button>
      </div>

      {cropModalImg && (
        <ImageCropModal
          image={cropModalImg}
          onClose={() => setCropModalImg(null)}
          onSave={async (img) => {
            setProfileImage(img);
            setConfirmRemove(false);
            setCropModalImg(null);
          }}
        />
      )}

      {showSuccessPopup && (
        <div className="modal-overlay" onClick={() => setShowSuccessPopup(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button
              type="button"
              className="modal-close-btn"
              onClick={() => setShowSuccessPopup(false)}
              aria-label="Close"
            >
              ×
            </button>
            <div style={{ textAlign: "center", padding: "12px 0" }}>
              <h3>Profile updated</h3>
              <p>Your profile changes were saved successfully.</p>
            </div>
            <button
              type="button"
              className="mock-btn"
              style={{ width: "100%", marginTop: 8 }}
              onClick={() => navigate("/")}
            >
              Continue
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default EditProfile;
