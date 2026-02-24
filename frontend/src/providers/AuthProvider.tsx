import React, { createContext, useContext, useEffect } from 'react';
import { useAuthStore } from '../lib/auth-store';
import { api } from '../lib/axios';

const AuthContext = createContext<null>(null);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const { setAuth, clearAuth, setLoading } = useAuthStore();

    useEffect(() => {
        const initAuth = async () => {
            const { accessToken } = useAuthStore.getState();
            if (!accessToken) {
                setLoading(false);
                return;
            }
            try {
                const response = await api.get('/auth/me');
                // Preserve tokens — /auth/me does not return them
                const state = useAuthStore.getState();
                setAuth(response.data, state.accessToken ?? accessToken, state.refreshToken);
            } catch (error) {
                clearAuth();
            } finally {
                setLoading(false);
            }
        };

        initAuth();
    }, []);

    return <AuthContext.Provider value={null}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
    const { user, isAuthenticated, isLoading, clearAuth } = useAuthStore();

    const login = async (credentials: any) => {
        const response = await api.post('/auth/login', credentials);
        const { access_token, refresh_token } = response.data;
        useAuthStore.getState().setAuth(null, access_token, refresh_token);
        const meResponse = await api.get('/auth/me');
        useAuthStore.getState().setAuth(meResponse.data, access_token, refresh_token);
    };

    const register = async (data: any) => {
        const response = await api.post('/auth/register', data);
        const { access_token, refresh_token } = response.data;
        useAuthStore.getState().setAuth(null, access_token, refresh_token);
        const meResponse = await api.get('/auth/me');
        useAuthStore.getState().setAuth(meResponse.data, access_token, refresh_token);
    };

    const logout = async () => {
        // Optional: await api.post('/auth/logout');
        clearAuth();
    };

    return {
        user,
        isAuthenticated,
        isLoading,
        login,
        register,
        logout,
    };
};
