import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { AuthState, User } from '../types/auth';

const AUTH_STORAGE_KEY = 'rag-auth';

export const useAuthStore = create<AuthState>()(
    persist(
        (set) => ({
            user: null,
            accessToken: null,
            refreshToken: null,
            isAuthenticated: false,
            isLoading: true,

            setAuth: (user: User | null, accessToken: string, refreshToken?: string | null) => {
                set((state) => ({
                    user: user ?? state.user,
                    accessToken: accessToken || state.accessToken,
                    refreshToken: refreshToken !== undefined ? refreshToken : state.refreshToken,
                    isAuthenticated: !!(accessToken || state.accessToken),
                    isLoading: false,
                }));
            },

            clearAuth: () => {
                set({
                    user: null,
                    accessToken: null,
                    refreshToken: null,
                    isAuthenticated: false,
                    isLoading: false,
                });
            },

            setLoading: (isLoading: boolean) => {
                set({ isLoading });
            },
        }),
        {
            name: AUTH_STORAGE_KEY,
            partialize: (state) => ({ accessToken: state.accessToken, refreshToken: state.refreshToken }),
        }
    )
);
