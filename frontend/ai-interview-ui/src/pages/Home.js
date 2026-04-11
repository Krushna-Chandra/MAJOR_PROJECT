import React from "react";
import { useNavigate } from "react-router-dom";
import { BrainCircuit, BriefcaseBusiness, Code2, FileSearch, Mic2, Sigma } from "lucide-react";
import analyticsImage from "../assets/Analytics.png";
import feedbackImage from "../assets/feedback.png";
import mockInterviewImage from "../assets/mock_interview.png";
import multiTypeInterviewImage from "../assets/multi_type_interview.png";
import resumeBasedInterviewImage from "../assets/resume_based_interview.png";
import voiceImage from "../assets/voice.png";
import "../App.css";

const howItWorksSteps = [
  {
    step: "01",
    title: "Choose your interview track",
    description:
      "Pick HR, technical, mock, aptitude, or resume-based practice depending on the role you want to target.",
    accent: "cyan",
    bullets: ["Role-based paths", "Fast topic selection", "Beginner to advanced"],
  },
  {
    step: "02",
    title: "Practice with realistic prompts",
    description:
      "Answer guided questions in a focused flow that feels like a real interview instead of a static form.",
    accent: "violet",
    bullets: ["Voice or typed answers", "Structured question flow", "Focused practice mode"],
  },
  {
    step: "03",
    title: "Get AI feedback instantly",
    description:
      "See strengths, weak spots, and improvement hints right after each round so you can correct faster.",
    accent: "amber",
    bullets: ["Immediate scoring", "Actionable tips", "Performance signals"],
  },
  {
    step: "04",
    title: "Track progress and improve",
    description:
      "Use your dashboard and reports to compare sessions, improve consistency, and build confidence over time.",
    accent: "emerald",
    bullets: ["Progress history", "Confidence building", "Smarter revision"],
  },
];

const benefits = [
  {
    stat: "24/7",
    title: "Practice on your schedule",
    description: "Train anytime without waiting for a coach or a live mock session.",
  },
  {
    stat: "Real",
    title: "Interview-like experience",
    description: "Build comfort with realistic flows so the actual round feels familiar.",
  },
  {
    stat: "AI",
    title: "Personalized improvement",
    description: "Get feedback tailored to your answers, pacing, and communication quality.",
  },
  {
    stat: "Growth",
    title: "Visible progress over time",
    description: "Review reports and performance trends to measure how much you improve.",
  },
  {
    stat: "Roles",
    title: "Built for multiple interview types",
    description: "Prepare for HR, technical, resume-based, mock, and aptitude rounds in one place.",
  },
  {
    stat: "Reports",
    title: "Structured performance reports",
    description: "Use analytics and session summaries to revise smarter before your real interview.",
  },
];

const features = [
  {
    badge: "Mock",
    title: "AI Mock Interviews",
    description: "Practice role-focused interviews with an AI flow that feels structured and realistic.",
    accent: "cyan",
    tags: ["Scenario based", "Adaptive prompts"],
    image: mockInterviewImage,
  },
  {
    badge: "Analytics",
    title: "Performance Dashboard",
    description: "Review scores, progress signals, and trends to understand where your interview skills are improving.",
    accent: "blue",
    tags: ["Reports", "Progress tracking"],
    image: analyticsImage,
  },
  {
    badge: "Feedback",
    title: "Smart Improvement Tips",
    description: "Receive guidance on clarity, confidence, structure, and delivery after each round.",
    accent: "amber",
    tags: ["Actionable", "Personalized"],
    image: feedbackImage,
  },
  {
    badge: "Resume",
    title: "Resume-Based Practice",
    description: "Upload your resume and prepare with questions tailored to your background and chosen role.",
    accent: "violet",
    tags: ["Resume aware", "Role aligned"],
    image: resumeBasedInterviewImage,
  },
  {
    badge: "Voice",
    title: "Voice Interview Experience",
    description: "Simulate spoken interview rounds with an experience designed to feel closer to real conversation.",
    accent: "emerald",
    tags: ["Speaking practice", "Natural flow"],
    image: voiceImage,
  },
  {
    badge: "Coverage",
    title: "Multi-Format Preparation",
    description: "Switch between HR, technical, aptitude, mock, and resume interview modes in one platform.",
    accent: "rose",
    tags: ["All-in-one", "Flexible prep"],
    image: multiTypeInterviewImage,
  },
];

function Home() {
  const navigate = useNavigate();
  const featureSectionRef = React.useRef(null);
  const [typedName, setTypedName] = React.useState("");
  const [activeStep, setActiveStep] = React.useState(0);
  const [zoomedImage, setZoomedImage] = React.useState(null);
  const [isZoomAnimating, setIsZoomAnimating] = React.useState(false);
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

  const userFirstName = React.useMemo(() => {
    const user = storedUser;
    if (!user) return "User";
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

    const firstName = userFirstName;
    let currentIndex = 0;
    let timeoutId;

    const tick = () => {
      if (currentIndex <= firstName.length) {
        setTypedName(firstName.slice(0, currentIndex));
      }

      if (currentIndex < firstName.length) {
        currentIndex += 1;
        timeoutId = window.setTimeout(tick, 120);
      } else {
        timeoutId = window.setTimeout(() => {
          currentIndex = 0;
          setTypedName("");
          timeoutId = window.setTimeout(() => {
            currentIndex = 1;
            setTypedName(firstName.slice(0, currentIndex));
            timeoutId = window.setTimeout(tick, 120);
          }, 400);
        }, 1400);
      }
    };

    timeoutId = window.setTimeout(() => {
      currentIndex = 1;
      setTypedName(firstName.slice(0, currentIndex));
      timeoutId = window.setTimeout(tick, 120);
    }, 400);

    return () => window.clearTimeout(timeoutId);
  }, [storedUser, userFirstName]);

  React.useEffect(() => {
    const intervalId = window.setInterval(() => {
      setActiveStep((current) => (current + 1) % howItWorksSteps.length);
    }, 4200);

    return () => window.clearInterval(intervalId);
  }, []);

  React.useEffect(() => {
    if (!zoomedImage) return undefined;

    const frameId = window.requestAnimationFrame(() => {
      setIsZoomAnimating(true);
    });

    return () => window.cancelAnimationFrame(frameId);
  }, [zoomedImage]);

  const goToPreviousStep = () => {
    setActiveStep((current) => (current - 1 + howItWorksSteps.length) % howItWorksSteps.length);
  };

  const goToNextStep = () => {
    setActiveStep((current) => (current + 1) % howItWorksSteps.length);
  };

  const closeZoomedImage = () => {
    setIsZoomAnimating(false);
    window.setTimeout(() => {
      setZoomedImage(null);
    }, 260);
  };

  return (
    <>
      {/* HERO - professional two-column layout */}
      <div className="mock-hero violet-hero reveal">
        <div style={{ maxWidth: 720 }}>
          {storedUser && (
            <div className="hero-greeting">
              <span className="hero-greeting-label">Welcome</span>
              <span className="hero-greeting-name">{typedName}</span>
              <span className="hero-greeting-cursor" aria-hidden="true" />
            </div>
          )}
          <h1>
            Practice. Improve.
            <br />
            Land the Job.
          </h1>
          <p>
            INTERVIEWR helps you prepare for interviews with AI-driven feedback and
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
          <svg className="mock-hero-img" viewBox="0 0 600 400" xmlns="http://www.w3.org/2000/svg" aria-label="Interview preparation illustration">
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
            <div className="category-icon"><BriefcaseBusiness size={30} strokeWidth={2.1} aria-label="HR" /></div>
            <h3>HR Interview</h3>
            <p>Communication & personality questions</p>
          </div>

          <div
            className="category-card category-tech"
            onClick={() => navigate("/technical-interview")}
          >
            <div className="category-icon"><Code2 size={30} strokeWidth={2.1} aria-label="Tech" /></div>
            <h3>Technical Interview</h3>
            <p>Programming & technical concepts</p>
          </div>

          <div
            className="category-card category-beh"
            onClick={() => navigate("/hr-interview")}
          >
            <div className="category-icon"><BrainCircuit size={30} strokeWidth={2.1} aria-label="Behavioral" /></div>
            <h3>Behavioral Interview</h3>
            <p>Situational & leadership questions</p>
          </div>

          <div
            className="category-card category-resume"
            onClick={() => navigate("/resume-interview")}
          >
            <div className="category-icon"><FileSearch size={30} strokeWidth={2.1} aria-label="Resume" /></div>
            <h3>Resume Interview</h3>
            <p>Upload resume and choose role</p>
          </div>

          <div
            className="category-card category-mock"
            onClick={() => navigate("/mock-interview")}
          >
            <div className="category-icon"><Mic2 size={30} strokeWidth={2.1} aria-label="Mock" /></div>
            <h3>Mock Interview</h3>
            <p>Simulated interview experience with feedback.</p>
          </div>

          <div
            className="category-card category-aptitude"
            onClick={() => navigate("/aptitude-test")}
          >
            <div className="category-icon"><Sigma size={30} strokeWidth={2.1} aria-label="Aptitude" /></div>
            <h3>Aptitude Test</h3>
            <p>Logical, quantitative, and verbal skills assessment.</p>
          </div>
        </div>
      </div>

      {/* FEATURES */}
      <div className="mock-section reveal feature-section-overlay-host" style={{ padding: "50px 0" }} ref={featureSectionRef}>
        <div className="section-heading section-heading-centered">
          <span className="section-heading-badge">Core Experience</span>
          <h2 className="section-heading-title section-heading-title-glow">Features</h2>
          <p className="section-heading-copy">
            Explore the key tools inside INTERVIEWR that help you practice smarter and improve faster.
          </p>
        </div>
        <div className="feature-grid">
          {features.map((item, index) => (
            <article key={item.title} className={`feature-card feature-card-${item.accent} feature-card-layout-${(index % 3) + 1}`}>
              <div className="feature-card-top">
                <span className="feature-card-badge">{item.badge}</span>
                <div className="feature-card-miniindex">0{index + 1}</div>
              </div>

              <div className="feature-card-visual" aria-hidden="true">
                {item.image ? (
                  <button
                    type="button"
                    className="feature-visual-button"
                    onClick={(event) => {
                      const sectionRect = featureSectionRef.current?.getBoundingClientRect();
                      const rect = event.currentTarget.getBoundingClientRect();
                      if (!sectionRect) return;
                      const targetWidth = Math.min(sectionRect.width - 48, 1120);
                      const targetHeight = Math.min(sectionRect.height - 48, window.innerHeight * 0.72);
                      setZoomedImage({
                        src: item.image,
                        originTop: rect.top - sectionRect.top,
                        originLeft: rect.left - sectionRect.left,
                        originWidth: rect.width,
                        originHeight: rect.height,
                        targetTop: Math.max(24, (sectionRect.height - targetHeight) / 2),
                        targetLeft: Math.max(24, (sectionRect.width - targetWidth) / 2),
                        targetWidth,
                      });
                    }}
                    aria-label={`Open full image for ${item.title}`}
                  >
                    <img className="feature-visual-image" src={item.image} alt={item.title} />
                  </button>
                ) : (
                  <>
                    <span className="feature-visual-orb feature-visual-orb-one" />
                    <span className="feature-visual-orb feature-visual-orb-two" />
                    <div className="feature-visual-screen">
                      <div className="feature-visual-screen-top">
                        <span />
                        <span />
                        <span />
                      </div>
                      <div className="feature-visual-screen-body">
                        <div className="feature-visual-line feature-visual-line-lg" />
                        <div className="feature-visual-line feature-visual-line-md" />
                        <div className="feature-visual-metrics">
                          <span />
                          <span />
                          <span />
                        </div>
                      </div>
                    </div>
                  </>
                )}
              </div>

              <div className="feature-card-copy">
                <h3>{item.title}</h3>
                <p>{item.description}</p>
                <div className="feature-card-tags">
                  {item.tags.map((tag) => (
                    <span key={tag}>{tag}</span>
                  ))}
                </div>
              </div>
            </article>
          ))}
        </div>

        {zoomedImage && (
          <div
            className="image-lightbox"
            role="dialog"
            aria-modal="true"
            onClick={closeZoomedImage}
          >
            <div
              className={`image-lightbox-content ${isZoomAnimating ? "is-open" : ""}`}
              style={{
                "--origin-top": `${zoomedImage.originTop}px`,
                "--origin-left": `${zoomedImage.originLeft}px`,
                "--origin-width": `${zoomedImage.originWidth}px`,
                "--origin-height": `${zoomedImage.originHeight}px`,
                "--target-top": `${zoomedImage.targetTop}px`,
                "--target-left": `${zoomedImage.targetLeft}px`,
                "--target-width": `${zoomedImage.targetWidth}px`,
              }}
              onClick={(event) => event.stopPropagation()}
            >
              <button
                type="button"
                className="image-lightbox-close"
                onClick={closeZoomedImage}
                aria-label="Close image preview"
              >
                x
              </button>
              <img className="image-lightbox-image" src={zoomedImage.src} alt="Full size preview" />
            </div>
          </div>
        )}

      </div>

      {/* HOW IT WORKS */}
      <div className="mock-section how-it-works-section reveal">
        <div className="section-heading section-heading-centered">
          <span className="section-heading-badge">Guided Journey</span>
          <h2 className="section-heading-title section-heading-title-glow">How It Works</h2>
          <p className="section-heading-copy">
            A smooth interview prep flow that keeps every step focused, visual, and easy to follow.
          </p>
        </div>
        <div className="how-it-works-shell">
          <div className="how-it-works-head">
            <div>
              <span className="how-it-works-kicker">Guided journey</span>
            </div>
            <div className="how-it-works-progress">
              {howItWorksSteps.map((item, index) => (
                <button
                  key={item.step}
                  type="button"
                  className={`how-it-works-dot ${index === activeStep ? "active" : ""}`}
                  onClick={() => setActiveStep(index)}
                  aria-label={`Show step ${item.step}`}
                />
              ))}
            </div>
          </div>

          <div className="how-it-works-carousel">
            <div
              className="how-it-works-track"
              style={{ transform: `translateX(-${activeStep * 100}%)` }}
            >
              {howItWorksSteps.map((item) => (
                <article key={item.step} className={`how-it-works-card accent-${item.accent}`}>
                  <div className="how-it-works-visual">
                    <div className="how-it-works-placeholder">
                      <div className="how-it-works-placeholder-top">
                        <span />
                        <span />
                        <span />
                      </div>
                      <div className="how-it-works-placeholder-main">
                        <div className="how-it-works-placeholder-chart" />
                        <div className="how-it-works-placeholder-stack">
                          <span />
                          <span />
                          <span />
                        </div>
                      </div>
                      <div className="how-it-works-placeholder-footer">
                        <span />
                        <span />
                      </div>
                    </div>
                  </div>

                  <div className="how-it-works-copy">
                    <div className="how-it-works-stepno">Step {item.step}</div>
                    <h4>{item.title}</h4>
                    <p>{item.description}</p>
                    <div className="how-it-works-tags">
                      {item.bullets.map((bullet) => (
                        <span key={bullet}>{bullet}</span>
                      ))}
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </div>

          <div className="how-it-works-controls">
            <button type="button" className="how-it-works-nav" onClick={goToPreviousStep}>
              Previous
            </button>
            <button type="button" className="how-it-works-nav how-it-works-nav-primary" onClick={goToNextStep}>
              Next
            </button>
          </div>
        </div>
      </div>

      {/* BENEFITS */}
      <div className="mock-section benefits-section reveal">
        <div className="section-heading section-heading-centered">
          <span className="section-heading-badge">Why INTERVIEWR</span>
          <h2 className="section-heading-title section-heading-title-glow">Benefits / Why Use It</h2>
          <p className="section-heading-copy">
            Everything in the platform is designed to help you practice faster, improve clearly, and walk into interviews with more confidence.
          </p>
        </div>
        <div className="benefits-shell">
          {benefits.map((item, index) => (
            <article key={item.title} className={`benefit-card benefit-card-${(index % 3) + 1}`}>
              <div className="benefit-card-stat">{item.stat}</div>
              <h3>{item.title}</h3>
              <p>{item.description}</p>
            </article>
          ))}
        </div>
      </div>

      {/* ABOUT SECTION */}
      <div id="about" className="mock-section" style={{ background: "#fff", padding: "40px 0", marginTop: 40 }}>
        <div className="section-title">About INTERVIEWR</div>
        <div style={{ maxWidth: 900, margin: "0 auto", color: "#333", lineHeight: 1.7 }}>
          <p>
            INTERVIEWR (AI Powered Interview System) is designed to help you practice, polish, and shine during real interviews — using modern AI feedback and interactive interview modes.
          </p>
          <p>
            Whether you’re interviewing for technical roles, HR rounds, or resume-based hiring, INTERVIEWR provides structured practice, scoring insights, and guidance to help you level up quickly.
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
      <div className="footer">© 2026 INTERVIEWR - AI Powered Interview System</div>

    </>
  );
}

export default Home;
