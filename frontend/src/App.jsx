import { useState, useEffect, useRef, useCallback } from "react";
import { useAuth } from "./AuthContext";
import CompanyList from "./components/CompanyList";
import CompanyDetail from "./components/CompanyDetail";
import AddCompany from "./components/AddCompany";
import Settings from "./components/Settings";
import ActivityTracker from "./components/ActivityTracker";
import BoobBusInfo from "./components/BoobBusInfo";
import "./App.css";

// Shuffle photos on each load
const DORIS_PHOTOS = Array.from({ length: 9 }, (_, i) => `/doris/doris-${i + 1}.png`)
  .sort(() => Math.random() - 0.5);

function LoginPage() {
  const { gsiReady, renderGoogleButton } = useAuth();
  const btnRef = useRef(null);

  useEffect(() => {
    if (gsiReady && btnRef.current) {
      renderGoogleButton(btnRef.current);
    }
  }, [gsiReady, renderGoogleButton]);

  return (
    <div className="login-page">
      <div className="login-photos">
        {DORIS_PHOTOS.map((src, i) => (
          <div key={i} className="login-photo" style={{ backgroundImage: `url(${src})` }} />
        ))}
      </div>
      <div className="login-overlay">
        <div className="login-card">
          <img src="/logo.png" alt="Boob Bus" className="login-logo" />
          <h1>The Boob Bus Co-Pilot</h1>
          <p className="login-subtitle">
            Lead generation & outreach for mobile mammography bookings
          </p>
          <div className="login-btn-wrapper">
            <div ref={btnRef} />
          </div>
          <p className="login-footer">
            In Loving Memory Of Doris Jean<br />
            <span className="login-footer-sub">the inspiration behind</span><br />
            <span className="login-footer-brand">The Boob Bus</span>
          </p>
        </div>
      </div>
    </div>
  );
}

function App() {
  const { user, loading, logout } = useAuth();
  const [selectedCompanyId, setSelectedCompanyId] = useState(null);
  const [view, setView] = useState("list");

  const navigate = useCallback((newView, companyId = null) => {
    setView(newView);
    setSelectedCompanyId(companyId);
    const path = companyId ? `/${newView}/${companyId}` : `/${newView === "list" ? "" : newView}`;
    window.history.pushState({ view: newView, companyId }, "", path);
  }, []);

  const openCompany = (id) => navigate("detail", id);

  const goBack = () => navigate("list");

  // Handle browser back/forward
  useEffect(() => {
    const handlePop = (e) => {
      const state = e.state;
      if (state) {
        setView(state.view || "list");
        setSelectedCompanyId(state.companyId || null);
      } else {
        setView("list");
        setSelectedCompanyId(null);
      }
    };
    window.addEventListener("popstate", handlePop);
    // Set initial state
    window.history.replaceState({ view: "list", companyId: null }, "", "/");
    return () => window.removeEventListener("popstate", handlePop);
  }, []);

  if (loading) {
    return (
      <div className="login-page">
        <img src="/logo.png" alt="Boob Bus" className="login-logo" />
        <p>Loading...</p>
      </div>
    );
  }

  if (!user) {
    return <LoginPage />;
  }

  return (
    <div className="app">
      <header className="app-header">
        <img
          src="/logo.png"
          alt="Boob Bus"
          className="header-logo"
          onClick={goBack}
        />
        <div className="header-text">
          <h1 onClick={goBack}>The Boob Bus Co-Pilot</h1>
          <p className="subtitle">
            Find HR contacts & book mobile mammography visits for Utah companies
          </p>
        </div>
        <div className="header-user">
          <nav className="header-nav">
            <button
              className={`btn btn-nav ${view === "list" || view === "detail" || view === "add" ? "active" : ""}`}
              onClick={goBack}
            >
              Companies
            </button>
            <button
              className={`btn btn-nav ${view === "activity" ? "active" : ""}`}
              onClick={() => navigate("activity")}
            >
              Activity
            </button>
            <button
              className={`btn btn-nav ${view === "boobbus-info" ? "active" : ""}`}
              onClick={() => navigate("boobbus-info")}
            >
              Boob Bus Info
            </button>
            <button
              className={`btn btn-nav ${view === "settings" ? "active" : ""}`}
              onClick={() => navigate("settings")}
            >
              Settings
            </button>
          </nav>
          {user.picture && (
            <img src={user.picture} alt="" className="user-avatar" />
          )}
          <button className="btn btn-logout" onClick={logout}>
            Sign out
          </button>
        </div>
      </header>

      <main className="app-main">
        {view === "list" && (
          <CompanyList onSelect={openCompany} onAdd={() => navigate("add")} />
        )}
        {view === "detail" && (
          <CompanyDetail companyId={selectedCompanyId} onBack={goBack} />
        )}
        {view === "add" && <AddCompany onBack={goBack} />}
        {view === "settings" && <Settings onBack={goBack} />}
        {view === "activity" && (
          <ActivityTracker onBack={goBack} onSelectCompany={openCompany} />
        )}
        {view === "boobbus-info" && <BoobBusInfo onBack={goBack} />}
      </main>
    </div>
  );
}

export default App;
