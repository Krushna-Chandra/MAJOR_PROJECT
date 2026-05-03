import React, { useEffect, useRef, useState } from "react";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import Navbar from "./components/Navbar";
import Footer from "./components/Footer";

/* MAIN PAGES */
import Home from "./pages/Home";
import Auth from "./pages/Auth";
import VerifyEmail from "./pages/VerifyEmail";
import Instructions from "./pages/Instructions";
import Permissions from "./pages/Permissions";
import Interview from "./pages/Interview";
import VoiceInterview from "./pages/VoiceInterview";
import EditProfile from "./pages/EditProfile";
import Topics from "./pages/Topics";
import DashboardPage from "./pages/DashboardPage";
import ResumeAnalyzer from "./pages/ResumeAnalyzer";
import ResumeAnalyzerResults from "./pages/ResumeAnalyzerResults";
import ResumeInterview from "./pages/ResumeInterview";
import AnalyzedResume from "./pages/AnalyzedResume";
import AboutUs from "./pages/AboutUs";
import Reports from "./pages/Reports";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";

/* NEW CATEGORY PAGES */
import HRInterview from "./pages/HRInterview";
import TechnicalInterview from "./pages/TechnicalInterview";
import MockInterview from "./pages/MockInterview";
import AptitudeTest from "./pages/AptitudeTest";
import AptitudeExam from "./pages/AptitudeExam";
import { isInterviewFullscreenGuardActive } from "./utils/interviewFullscreenGuard";

/* PROTECTED ROUTE */
import ProtectedRoute from "./ProtectedRoute";

const ROUTE_EXIT_TRANSITION_MS = 280;

const isHomeRoute = (pathname) => pathname === "/";
const usesMainNavbar = (pathname) =>
  ["/", "/about", "/dashboard", "/resume-analyzer", "/resume-analyzer/results"].includes(pathname);
const usesFooter = (pathname) =>
  ["/", "/dashboard", "/about"].includes(pathname);
const isInterviewFullscreenRoute = (pathname) =>
  ["/instructions", "/permissions", "/interview", "/voice-interview"].includes(pathname);

function ScrollRevealManager() {
  const location = useLocation();

  useEffect(() => {
    const observeRevealElements = (observer) => {
      document.querySelectorAll(".reveal").forEach((el) => {
        if (!el.classList.contains("visible")) {
          observer.observe(el);
        }
      });
    };

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

    observeRevealElements(observer);

    const mutationObserver = new MutationObserver(() => {
      observeRevealElements(observer);
    });

    mutationObserver.observe(document.body, {
      childList: true,
      subtree: true,
    });

    return () => {
      mutationObserver.disconnect();
      observer.disconnect();
    };
  }, [location.pathname]);

  return null;
}

function HashScrollManager() {
  const location = useLocation();

  useEffect(() => {
    if (!location.hash) {
      return undefined;
    }

    const hashTarget = location.hash.replace("#", "");

    const scrollToTarget = () => {
      const element = document.getElementById(hashTarget);
      if (element) {
        element.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    };

    const timeoutId = window.setTimeout(scrollToTarget, 120);

    return () => window.clearTimeout(timeoutId);
  }, [location.hash, location.pathname]);

  return null;
}

function AppRoutes({ routeLocation }) {
  return (
    <Routes location={routeLocation}>
      {/* ---------------- PUBLIC ROUTES ---------------- */}
      <Route path="/" element={<Home />} />
      <Route path="/auth" element={<Auth />} />
      <Route path="/verify-email" element={<VerifyEmail />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />

      {/* ABOUT US PAGE */}
      <Route path="/about" element={<AboutUs />} />
      {/* face login removed */}

      {/* ---------------- INTERVIEW CATEGORY ROUTES ---------------- */}
      <Route
        path="/hr-interview"
        element={
          <ProtectedRoute>
            <HRInterview />
          </ProtectedRoute>
        }
      />

      <Route
        path="/technical-interview"
        element={
          <ProtectedRoute>
            <TechnicalInterview />
          </ProtectedRoute>
        }
      />

      {/* TOPICS ROUTE */}
      <Route
        path="/topics/:category"
        element={
          <ProtectedRoute>
            <Topics />
          </ProtectedRoute>
        }
      />

      {/* face registration route removed */}

      {/* ---------------- INTERVIEW FLOW ROUTES ---------------- */}
      <Route
        path="/instructions"
        element={
          <ProtectedRoute>
            <Instructions />
          </ProtectedRoute>
        }
      />

      <Route
        path="/permissions"
        element={
          <ProtectedRoute>
            <Permissions />
          </ProtectedRoute>
        }
      />

      <Route
        path="/interview"
        element={
          <ProtectedRoute>
            <Interview />
          </ProtectedRoute>
        }
      />

      <Route
        path="/voice-interview"
        element={
          <ProtectedRoute>
            <VoiceInterview />
          </ProtectedRoute>
        }
      />

      <Route
        path="/reports/:sessionId"
        element={
          <ProtectedRoute>
            <Reports />
          </ProtectedRoute>
        }
      />

      <Route
        path="/results/:sessionId"
        element={
          <ProtectedRoute>
            <Reports />
          </ProtectedRoute>
        }
      />

      <Route
        path="/resume-analyzer"
        element={
          <ProtectedRoute>
            <ResumeAnalyzer />
          </ProtectedRoute>
        }
      />

      <Route
        path="/resume-analyzer/results"
        element={
          <ProtectedRoute>
            <ResumeAnalyzerResults />
          </ProtectedRoute>
        }
      />

      <Route
        path="/resume-interview"
        element={
          <ProtectedRoute>
            <ResumeInterview />
          </ProtectedRoute>
        }
      />

      <Route
        path="/analyzed-resume"
        element={
          <ProtectedRoute>
            <AnalyzedResume />
          </ProtectedRoute>
        }
      />

      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />

      {/* ---------------- PROFILE ROUTE ---------------- */}
      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <EditProfile />
          </ProtectedRoute>
        }
      />

      {/* ---------------- NEW INTERVIEW TYPES ---------------- */}
      <Route
        path="/mock-interview"
        element={
          <ProtectedRoute>
            <MockInterview />
          </ProtectedRoute>
        }
      />
      <Route
        path="/aptitude-test"
        element={
          <ProtectedRoute>
            <AptitudeTest />
          </ProtectedRoute>
        }
      />
      <Route
        path="/aptitude-exam"
        element={
          <ProtectedRoute>
            <AptitudeExam />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}

function AnimatedRoutes() {
  const location = useLocation();
  const [displayLocation, setDisplayLocation] = useState(location);
  const [transitionStage, setTransitionStage] = useState("enter");
  const nextLocationRef = useRef(location);

  useEffect(() => {
    const currentPath = `${location.pathname}${location.search}${location.hash}`;
    const displayPath = `${displayLocation.pathname}${displayLocation.search}${displayLocation.hash}`;

    if (currentPath !== displayPath || location.key !== displayLocation.key) {
      nextLocationRef.current = location;

      const shouldSkipTransition =
        isHomeRoute(displayLocation.pathname) ||
        isHomeRoute(location.pathname) ||
        (isInterviewFullscreenGuardActive() &&
          (isInterviewFullscreenRoute(displayLocation.pathname) ||
            isInterviewFullscreenRoute(location.pathname)));

      if (shouldSkipTransition) {
        setDisplayLocation(location);
        setTransitionStage("enter");
        return;
      }

      setTransitionStage("exit");
    }
  }, [displayLocation, location]);

  useEffect(() => {
    if (transitionStage !== "exit") {
      return undefined;
    }

    const timeoutId = window.setTimeout(() => {
      setDisplayLocation(nextLocationRef.current);
      setTransitionStage("enter");
    }, ROUTE_EXIT_TRANSITION_MS);

    return () => window.clearTimeout(timeoutId);
  }, [transitionStage]);

  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: "auto" });
  }, [displayLocation.pathname, displayLocation.search, displayLocation.hash]);

  const routeKey =
    displayLocation.key ||
    `${displayLocation.pathname}${displayLocation.search}${displayLocation.hash}`;
  const routeTransitionClassName = isHomeRoute(displayLocation.pathname)
    ? "route-transition route-transition--home"
    : `route-transition route-transition--${transitionStage}`;
  const showMainNavbar = usesMainNavbar(displayLocation.pathname);
  const showFooter = usesFooter(displayLocation.pathname);

  return (
    <>
      {showMainNavbar ? <Navbar /> : null}
      <div className="route-transition-shell">
        <div
          key={routeKey}
          className={routeTransitionClassName}
        >
          <AppRoutes routeLocation={displayLocation} />
        </div>
      </div>
      {showFooter ? <Footer /> : null}
    </>
  );
}

function App() {
  return (
    <BrowserRouter>
      <ScrollRevealManager />
      <HashScrollManager />
      <AnimatedRoutes />
    </BrowserRouter>
  );
}

export default App;
