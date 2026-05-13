import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { AuthResponse, User, apiFetch } from "@/lib/api";

type AuthContextValue = {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
};

const TOKEN_KEY = "liquid_chat_token";
const USER_KEY = "liquid_chat_user";

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    const savedToken = localStorage.getItem(TOKEN_KEY);
    const savedUser = localStorage.getItem(USER_KEY);
    if (savedToken) setToken(savedToken);
    if (savedUser) {
      try {
        setUser(JSON.parse(savedUser) as User);
      } catch {
        localStorage.removeItem(USER_KEY);
      }
    }
  }, []);

  const saveSession = useCallback((auth: AuthResponse) => {
    localStorage.setItem(TOKEN_KEY, auth.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(auth.user));
    setToken(auth.access_token);
    setUser(auth.user);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const auth = await apiFetch<AuthResponse>("/api/auth/login", null, {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    saveSession(auth);
  }, [saveSession]);

  const register = useCallback(async (name: string, email: string, password: string) => {
    const auth = await apiFetch<AuthResponse>("/api/auth/register", null, {
      method: "POST",
      body: JSON.stringify({ name, email, password }),
    });
    saveSession(auth);
  }, [saveSession]);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setToken(null);
    setUser(null);
  }, []);

  const value = useMemo<AuthContextValue>(() => ({
    token,
    user,
    isAuthenticated: Boolean(token && user),
    login,
    register,
    logout,
  }), [token, user, login, register, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return value;
}
