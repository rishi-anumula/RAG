import React, { createContext, useContext, useState, useEffect } from 'react';
import type { User, LoginCredentials, SignupCredentials } from '../types';
import { authService } from '../services/authService';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  signup: (credentials: SignupCredentials) => Promise<void>;
  guestLogin: () => void;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check saved session on mount
    const savedUser = authService.getCurrentUser();
    const token = localStorage.getItem('rag_token');

    if (savedUser && token) {
      setUser(savedUser);
    } else {
      // Default auto-login as guest for seamless access if no token exists
      const guestUser: User = { 
        id: '00000000-0000-0000-0000-000000000000', 
        email: 'guest@example.com' 
      };
      localStorage.setItem('rag_token', 'mock-guest-token');
      localStorage.setItem('rag_user', JSON.stringify(guestUser));
      setUser(guestUser);
    }
    setLoading(false);
  }, []);

  const login = async (credentials: LoginCredentials) => {
    setLoading(true);
    try {
      const response = await authService.login(credentials);
      if (response.user) {
        setUser(response.user);
      }
    } finally {
      setLoading(false);
    }
  };

  const signup = async (credentials: SignupCredentials) => {
    setLoading(true);
    try {
      const response = await authService.signup(credentials);
      if (response.user) {
        // If session was returned upon signup, save it
        if (response.session) {
          localStorage.setItem('rag_token', response.session.access_token);
          localStorage.setItem('rag_user', JSON.stringify(response.user));
          setUser(response.user);
        } else {
          // Fallback login
          await login(credentials);
        }
      }
    } finally {
      setLoading(false);
    }
  };

  const guestLogin = () => {
    const guestUser: User = { 
      id: '00000000-0000-0000-0000-000000000000', 
      email: 'guest@example.com' 
    };
    localStorage.setItem('rag_token', 'mock-guest-token');
    localStorage.setItem('rag_user', JSON.stringify(guestUser));
    setUser(guestUser);
  };

  const logout = () => {
    authService.logout();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ 
      user, 
      loading, 
      login, 
      signup, 
      guestLogin, 
      logout,
      isAuthenticated: !!user && !!localStorage.getItem('rag_token')
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default useAuth;
