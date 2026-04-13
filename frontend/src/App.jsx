import { useState, useEffect, useRef } from "react";
import { useAuth } from "./AuthContext";
import CompanyList from "./components/CompanyList";
import CompanyDetail from "./components/CompanyDetail";
import AddCompany from "./components/AddCompany";
import Settings from "./components/Settings";
import ActivityTracker from "./components/ActivityTracker";
import BoobBusInfo from "./components/BoobBusInfo";
import "./App.css";

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
      <img src="/logo.png" alt="Boob Bus" className="login-logo" />
      <h1>Boob Bus HQ</h1>
      <p className="login-subtitle">
        Lead generation & outreach for mobile mammography bookings
      </p>
      <div className="login-btn-wrapper">
        <div ref={btnRef} />
      </div>
      <p className="login-footer">
        Sign in with Google to access the dashboard
      </p>
    </div>
  );
}

function App() {
  const { user, loading, logout } = useAuth();
  const [selectedCompanyId, setSelectedCompanyId] = useState(null);
  const [view, setView] = useState("list");

  const openCompany = (id) => {
    setSelectedCompanyId(id);
    setView("detail");
  };

  const goBack = () => {
    setSelectedCompanyId(null);
    setView("list");
  };

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
          <h1 onClick={goBack}>Boob Bus HQ</h1>
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
              onClick={() => setView("activity")}
            >
              Activity
            </button>
            <button
              className={`btn btn-nav ${view === "boobbus-info" ? "active" : ""}`}
              onClick={() => setView("boobbus-info")}
            >
              Boob Bus Info
            </button>
            <button
              className={`btn btn-nav ${view === "settings" ? "active" : ""}`}
              onClick={() => setView("settings")}
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
          <CompanyList onSelect={openCompany} onAdd={() => setView("add")} />
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
