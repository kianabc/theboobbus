import { useState } from "react";
import CompanyList from "./components/CompanyList";
import CompanyDetail from "./components/CompanyDetail";
import AddCompany from "./components/AddCompany";
import "./App.css";

function App() {
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

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <h1 onClick={goBack} style={{ cursor: "pointer" }}>
            Utah HR Email Finder
          </h1>
          <p className="subtitle">
            Find HR department contacts for top Utah companies
          </p>
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
      </main>
    </div>
  );
}

export default App;
