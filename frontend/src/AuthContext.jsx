import { createContext, useContext, useState, useEffect, useCallback } from "react";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);
  const [gsiReady, setGsiReady] = useState(false);

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
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    setToken(null);
    localStorage.removeItem("google_token");
    if (window.google?.accounts?.id) {
      window.google.accounts.id.disableAutoSelect();
    }
  }, []);

  // Render the Google button into a given DOM element
  const renderGoogleButton = useCallback((el) => {
    if (!el || !window.google?.accounts?.id) return;
    window.google.accounts.id.renderButton(el, {
      theme: "outline",
      size: "large",
      text: "signin_with",
      shape: "pill",
      width: 300,
    });
  }, []);

  // Restore session from localStorage
  useEffect(() => {
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

  // Wait for GSI script to load, then initialize
  useEffect(() => {
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
    if (!clientId) return;

    const init = () => {
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: handleCredentialResponse,
        auto_select: true,
      });
      setGsiReady(true);
    };

    if (window.google?.accounts?.id) {
      init();
    } else {
      const interval = setInterval(() => {
        if (window.google?.accounts?.id) {
          clearInterval(interval);
          init();
        }
      }, 100);
      return () => clearInterval(interval);
    }
  }, [handleCredentialResponse]);

  return (
    <AuthContext.Provider value={{ user, token, loading, logout, gsiReady, renderGoogleButton }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
