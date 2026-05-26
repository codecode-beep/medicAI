import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User } from '../lib/api';

interface AuthState {
  token: string | null;
  user: User | null;
  setAuth: (token: string, user: User) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      setAuth: (token, user) => {
        localStorage.setItem('token', token);
        set({ token, user });
      },
      logout: () => {
        localStorage.removeItem('token');
        localStorage.removeItem('medintel-auth');
        set({ token: null, user: null });
      },
    }),
    {
      name: 'medintel-auth',
      onRehydrateStorage: () => (state) => {
        if (state?.token) {
          localStorage.setItem('token', state.token);
        }
      },
    }
  )
);

interface AppState {
  saveToHistory: boolean;
  toggleSaveToHistory: () => void;
  chatSessionId: string | null;
  setChatSessionId: (id: string) => void;
}

export const useAppStore = create<AppState>((set) => ({
  saveToHistory: false,
  toggleSaveToHistory: () => set((s) => ({ saveToHistory: !s.saveToHistory })),
  chatSessionId: null,
  setChatSessionId: (id) => set({ chatSessionId: id }),
}));
