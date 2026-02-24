export interface User {
  id: string;
  email: string;
  full_name: string;
  role: 'admin' | 'user';
  client_id: string;
  created_at: string;
}

export interface Client {
  id: string;
  name: string;
  slug: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setAuth: (user: User | null, accessToken: string, refreshToken?: string | null) => void;
  clearAuth: () => void;
  setLoading: (isLoading: boolean) => void;
}
