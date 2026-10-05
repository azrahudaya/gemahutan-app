"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { api } from "./api";

export interface AuthUser {
  id: number;
  email: string;
  role: string;
}

interface AuthState {
  isAuthenticated: boolean;
  loading: boolean;
  user: AuthUser | null;
  login: (email: string, password: string) => Promise<string>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState>({
  isAuthenticated: false,
  loading: true,
  user: null,
  login: async () => "",
  register: async () => {},
  logout: () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<AuthUser | null>(null);

  const loadUser = async (): Promise<AuthUser | null> => {
    try {
      const me = await api.getMe();
      const u = { id: me.id, email: me.email, role: me.role };
      setUser(u);
      return u;
    } catch {
      // Token kedaluwarsa atau tidak valid: biarkan kosong, halaman akan
      // mengalihkan ke login lewat status autentikasi.
      setUser(null);
      return null;
    }
  };

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    setIsAuthenticated(!!token);
    if (token) {
      // Tunggu hasil /me sebelum loading selesai, supaya halaman tidak sempat
      // mengira pengguna belum masuk dan membuat sesi tamu baru.
      void loadUser().finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (email: string, password: string): Promise<string> => {
    const res = await api.login(email, password);
    localStorage.setItem("access_token", res.access_token);
    localStorage.setItem("refresh_token", res.refresh_token);
    // Token tamu dari halaman depan dibuang saat petugas masuk.
    localStorage.removeItem("sesi_tamu");
    setIsAuthenticated(true);
    const u = await loadUser();
    return u?.role ?? "";
  };

  const register = async (name: string, email: string, password: string) => {
    // Daftar mengembalikan UserResponse, lalu klien login untuk dapat token.
    await api.register({ name, email, password });
    await login(email, password);
  };

  const logout = () => {
    const refreshToken = localStorage.getItem("refresh_token");
    api.logout(refreshToken).catch(() => {});
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("sesi_tamu");
    setIsAuthenticated(false);
    setUser(null);
    window.location.href = "/login";
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, loading, user, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
