import React from "react";
import { useNavigate } from "react-router-dom";
import "../App.css";
import Navbar from "../components/Navbar";

function Home() {
  const navigate = useNavigate();
  const [typedName, setTypedName] = React.useState("");
  const [storedUser, setStoredUser] = React.useState(() => {
    try {
      return JSON.parse(localStorage.getItem("user"));
    } catch {
      return null;
    }
  });

  React.useEffect(() => {
    const handleAuthChange = () => {
      try {
        setStoredUser(JSON.parse(localStorage.getItem("user")));
      } catch {
        setStoredUser(null);
      }
    };

    window.addEventListener("authchange", handleAuthChange);
    window.addEventListener("storage", handleAuthChange);

    return () => {
      window.removeEventListener("authchange", handleAuthChange);
      window.removeEventListener("storage", handleAuthChange);
    };
  }, []);

  const userDisplayName = React.useMemo(() => {
    const user = storedUser;
    if (!user) return "User";
    if (user.first_name && user.last_name) return `${user.first_name} ${user.last_name}`;
    if (user.first_name) return user.first_name;
    if (user.last_name) return user.last_name;
    if (user.email) return user.email.split("@")[0];
    return "User";
  }, [storedUser]);

  React.useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.2 }
    );

    document.querySelectorAll(".reveal").forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  React.useEffect(() => {
    if (!storedUser) {
      setTypedName("");
      return;
    }

    const fullName = userDisplayName;
    let currentIndex = 0;
    let timeoutId;

    const tick = () => {
      if (currentIndex <= fullName.length) {
        setTypedName(fullName.slice(0, currentIndex));
      }

      if (currentIndex < fullName.length) {
        currentIndex += 1;
        timeoutId = window.setTimeout(tick, 120);
      } else {
        timeoutId = window.setTimeout(() => {
          currentIndex = 0;
          setTypedName("");
          timeoutId = window.setTimeout(() => {
            currentIndex = 1;
            setTypedName(fullName.slice(0, currentIndex));
            timeoutId = window.setTimeout(tick, 120);
          }, 400);
        }, 1400);
      }
    };

    timeoutId = window.setTimeout(() => {
      currentIndex = 1;
      setTypedName(fullName.slice(0, currentIndex));
      timeoutId = window.setTimeout(tick, 120);
    }, 400);

    return () => window.clearTimeout(timeoutId);
  }, [storedUser, userDisplayName]);

  return (
    <>
      <Navbar />

      {/* HERO - professional two-column layout */}
      <div className="mock-hero violet-hero reveal">
        <div style={{ maxWidth: 720 }}>
          {storedUser && (
            <div className="hero-greeting">
              <span className="hero-greeting-label">Welcome back</span>
              <span className="hero-greeting-name">{typedName}</span>
              <span className="hero-greeting-cursor" />
            </div>
          )}
          <h1>Practice. Improve. Land the Job.</h1>
          <p>
            APIS helps you prepare for interviews with AI-driven feedback and
            realistic mock interviews — all in one polished experience.
          </p>

          <div style={{ marginTop: 22 }}>
            <button className="mock-btn" onClick={() => navigate("/hr-interview")}>Browse Categories</button>
            <button
              className="mock-btn"
              style={{ marginLeft: 12, background: "rgba(255,255,255,0.18)", color: "#fff" }}
              onClick={() => navigate("/topics/hr")}
            >
              Quick Interview
            </button>
          </div>
        </div>

        <div>
          {/* simple illustrative SVG */}
          <svg className="mock-hero-img" viewBox="0 0 600 400" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <linearGradient id="g1" x1="0" x2="1">
                <stop offset="0" stopColor="#fff" stopOpacity="0.18" />
                <stop offset="1" stopColor="#fff" stopOpacity="0.06" />
              </linearGradient>
            </defs>
            <rect x="0" y="0" width="600" height="400" rx="24" fill="url(#g1)" />
            <g transform="translate(40,24)">
              <rect x="0" y="0" width="260" height="160" rx="14" fill="#fff" opacity="0.12" />
              <rect x="300" y="40" width="220" height="120" rx="14" fill="#fff" opacity="0.08" />
              <circle cx="190" cy="220" r="70" fill="#fff" opacity="0.06" />
              <g transform="translate(40,16)" fill="#fff" opacity="0.95">
                <rect x="8" y="8" width="44" height="8" rx="4" />
                <rect x="8" y="26" width="110" height="8" rx="4" />
                <rect x="8" y="44" width="80" height="8" rx="4" />
              </g>
            </g>
          </svg>
        </div>
      </div>

      {/* STATS / HIGHLIGHTS */}
      <div className="reveal" style={{ maxWidth: 1100, margin: "30px auto 0", padding: "0 40px" }}>
        <div className="mistake-box" style={{ gap: 18 }}>
          <div>
            <h3 style={{ margin: 0 }}>Trusted by learners worldwide</h3>
            <p style={{ marginTop: 8, color: "#444" }}>
              Thousands of mock interviews, real feedback and measurable growth.
            </p>
          </div>

          <div style={{ display: "flex", gap: 18, alignItems: "center" }}>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 22, fontWeight: 800 }}>4.8</div>
              <div style={{ fontSize: 12, color: "#555" }}>Average Rating</div>
            </div>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 22, fontWeight: 800 }}>120k+</div>
              <div style={{ fontSize: 12, color: "#555" }}>Practice Sessions</div>
            </div>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 22, fontWeight: 800 }}>95%</div>
              <div style={{ fontSize: 12, color: "#555" }}>Improved Confidence</div>
            </div>
          </div>
        </div>
      </div>

      {/* CATEGORIES */}
      <div className="container reveal">
        <h2 style={{ textAlign: "center" }}>Interview Categories</h2>

        <div className="category-grid">
          <div
            className="category-card category-hr"
            onClick={() => navigate("/hr-interview")}
          >
            <div className="category-icon"><span role="img" aria-label="HR">💬</span></div>
            <h3>HR Interview</h3>
            <p>Communication & personality questions</p>
          </div>

          <div
            className="category-card category-tech"
            onClick={() => navigate("/technical-interview")}
          >
            <div className="category-icon"><span role="img" aria-label="Tech">💻</span></div>
            <h3>Technical Interview</h3>
            <p>Programming & technical concepts</p>
          </div>

          <div
            className="category-card category-beh"
            onClick={() => navigate("/hr-interview")}
          >
            <div className="category-icon"><span role="img" aria-label="Behavioral">🧠</span></div>
            <h3>Behavioral Interview</h3>
            <p>Situational & leadership questions</p>
          </div>

          <div
            className="category-card category-resume"
            onClick={() => navigate("/resume-interview")}
          >
            <div className="category-icon"><span role="img" aria-label="Resume">📄</span></div>
            <h3>Resume Interview</h3>
            <p>Upload resume and choose role</p>
          </div>

          <div
            className="category-card category-mock"
            onClick={() => navigate("/mock-interview")}
          >
            <div className="category-icon"><span role="img" aria-label="Mock">🎤</span></div>
            <h3>Mock Interview</h3>
            <p>Simulated interview experience with feedback.</p>
          </div>

          <div
            className="category-card category-aptitude"
            onClick={() => navigate("/aptitude-test")}
          >
            <div className="category-icon"><span role="img" aria-label="Aptitude">🧮</span></div>
            <h3>Aptitude Test</h3>
            <p>Logical, quantitative, and verbal skills assessment.</p>
          </div>
        </div>
      </div>

      {/* FEATURES */}
      <div className="mock-section reveal" style={{ padding: "50px 0" }}>
        <div className="section-title">⚡ Features</div>
        <div className="mock-grid">
          <div className="mock-card">
            <div className="card-top">
              <div>
                <h4>🤖 AI Mock Interviews</h4>
                <p style={{ marginTop: 6 }}>Practice real interview questions with AI scoring and feedback.</p>
              </div>
            </div>
          </div>

          <div className="mock-card">
            <div className="card-top">
              <div>
                <h4>📊 Performance Analytics</h4>
                <p style={{ marginTop: 6 }}>Track your progress with charts, scores, and trend insights.</p>
              </div>
            </div>
          </div>

          <div className="mock-card">
            <div className="card-top">
              <div>
                <h4>🧠 Smart Feedback</h4>
                <p style={{ marginTop: 6 }}>Get actionable tips on confidence, structure, and delivery.</p>
              </div>
            </div>
          </div>

          <div className="mock-card">
            <div className="card-top">
              <div>
                <h4>📄 Resume Analysis</h4>
                <p style={{ marginTop: 6 }}>Upload your resume and receive improvement suggestions.</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* HOW IT WORKS */}
      <div className="mock-section reveal" style={{ background: "#fff", padding: "50px 0" }}>
        <div className="section-title">🎥 How It Works</div>
        <div style={{ maxWidth: 900, margin: "0 auto" }}>
          <div style={{ display: "grid", gap: 14, paddingTop: 16 }}>
            <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
              <div style={{ fontSize: 22, fontWeight: 700 }}>1.</div>
              <div>
                <strong>Choose interview type</strong>
                <div style={{ color: "#555" }}>Pick HR, Technical, Behavioral, Resume review and more.</div>
              </div>
            </div>
            <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
              <div style={{ fontSize: 22, fontWeight: 700 }}>2.</div>
              <div>
                <strong>Answer questions</strong>
                <div style={{ color: "#555" }}>Speak or type responses to realistic prompts.</div>
              </div>
            </div>
            <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
              <div style={{ fontSize: 22, fontWeight: 700 }}>3.</div>
              <div>
                <strong>Get AI feedback</strong>
                <div style={{ color: "#555" }}>Receive scoring, pacing, and strength/weakness analysis.</div>
              </div>
            </div>
            <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
              <div style={{ fontSize: 22, fontWeight: 700 }}>4.</div>
              <div>
                <strong>Improve & track progress</strong>
                <div style={{ color: "#555" }}>Use your dashboard to compare past sessions and level up.</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* BENEFITS */}
      <div className="mock-section reveal" style={{ padding: "50px 0" }}>
        <div className="section-title">📊 Benefits / Why Use It</div>
        <div style={{ maxWidth: 900, margin: "0 auto" }}>
          <ul style={{ listStyle: "none", padding: 0, marginTop: 16, color: "#333" }}>
            <li style={{ marginBottom: 12 }}>✅ Practice anytime, anywhere.</li>
            <li style={{ marginBottom: 12 }}>✅ Real interview simulation you can revisit.</li>
            <li style={{ marginBottom: 12 }}>✅ Personalized feedback that helps you improve.</li>
            <li style={{ marginBottom: 12 }}>✅ Build confidence and track your progress with your dashboard.</li>
          </ul>
        </div>
      </div>

      {/* ABOUT SECTION */}
      <div id="about" className="mock-section" style={{ background: "#fff", padding: "40px 0", marginTop: 40 }}>
        <div className="section-title">About APIS</div>
        <div style={{ maxWidth: 900, margin: "0 auto", color: "#333", lineHeight: 1.7 }}>
          <p>
            APIS (AI Powered Interview System) is designed to help you practice, polish, and shine during real interviews — using modern AI feedback and interactive interview modes.
          </p>
          <p>
            Whether you’re interviewing for technical roles, HR rounds, or resume-based hiring, APIS provides structured practice, scoring insights, and guidance to help you level up quickly.
          </p>
          <p>Need help? Reach out via our support channels or check the FAQ at the bottom of the page.</p>
        </div>
      </div>

      {/* CTA SECTION */}
      <div className="mock-section cta-section reveal" style={{ padding: "70px 30px", marginTop: 40 }}>
        <div style={{ maxWidth: 900, margin: "0 auto", textAlign: "center" }}>
          <h2 style={{ margin: 0 }}>Start your AI Interview Journey Today</h2>
          <p style={{ marginTop: 12, fontSize: 18, opacity: 0.9 }}>
            Dive into a real mock interview and get instant AI feedback to sharpen your skills.
          </p>
          <button
            className="mock-btn"
            style={{ marginTop: 24 }}
            onClick={() => navigate("/mock-interview")}
          >
            Start Interview
          </button>
        </div>
      </div>

      {/* FOOTER */}
      <div className="footer">© 2026 APIS - AI Powered Interview System</div>
    </>
  );
}

export default Home;
