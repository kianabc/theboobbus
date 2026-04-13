import { createContext, useContext, useState, useEffect, useCallback, useRef } from "react";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);
  const btnRef = useRef(null);

  const handleCredentialResponse = useCallback((response) => {
    const credential = response.credential;
    try {
      const payload = JSON.parse(atob(credential.split(".")[1]));
      setUser({
        email: payload.email,
        name: payload.name,
        picture: payload.picture,
      });
      setToken(credential);
      localStorage.setItem("google_token", credential);
    } catch {
      console.error("Failed to decode Google token");
    }
    setLoading(false);
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    setToken(null);
    localStorage.removeItem("google_token");
    if (window.google?.accounts?.id) {
      window.google.accounts.id.disableAutoSelect();
    }
  }, []);

  useEffect(() => {
    // Try restoring from localStorage
    const saved = localStorage.getItem("google_token");
    if (saved) {
      try {
        const payload = JSON.parse(atob(saved.split(".")[1]));
        if (payload.exp * 1000 > Date.now()) {
          setUser({
            email: payload.email,
            name: payload.name,
            picture: payload.picture,
          });
          setToken(saved);
        } else {
          localStorage.removeItem("google_token");
        }
      } catch {
        localStorage.removeItem("google_token");
      }
    }
    setLoading(false);
  }, []);

  // Initialize GSI when the script loads
  useEffect(() => {
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
    if (!clientId) return;

    const initGsi = () => {
      if (!window.google?.accounts?.id) return;
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: handleCredentialResponse,
        auto_select: true,
      });
      // Render the button if we're not logged in
      if (!token && btnRef.current) {
        window.google.accounts.id.renderButton(btnRef.current, {
          theme: "outline",
          size: "large",
          text: "signin_with",
          shape: "pill",
          width: 300,
        });
      }
    };

    // GSI script might already be loaded or still loading
    if (window.google?.accounts?.id) {
      initGsi();
    } else {
      const interval = setInterval(() => {
        if (window.google?.accounts?.id) {
          clearInterval(interval);
          initGsi();
        }
      }, 100);
      return () => clearInterval(interval);
    }
  }, [handleCredentialResponse, token]);

  return (
    <AuthContext.Provider value={{ user, token, loading, logout, btnRef }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
