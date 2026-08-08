import React, { createContext, useContext, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import type { User, LoginCredentials, SignupCredentials } from '../types';
import { authService } from '../services/authService';
import { supabase } from '../services/supabaseClient';

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
  const navigate = useNavigate();

  useEffect(() => {
    console.log('[Auth Hook]: Initializing AuthProvider with window.location.href:', window.location.href);

    // 1. Initial check for existing local session / user
    const savedUser = authService.getCurrentUser();
    const token = localStorage.getItem('rag_token');

    if (token === 'mock-guest-token') {
      localStorage.removeItem('rag_token');
      localStorage.removeItem('rag_user');
      setUser(null);
    } else if (savedUser && token) {
      setUser(savedUser);
    } else {
      setUser(null);
    }

    // 2. Fetch active Supabase session if available
    supabase.auth.getSession().then((res) => {
      if (res?.error) {
        console.warn('[Auth Hook]: Error restoring Supabase session:', res.error.message);
      }
      const session = res?.data?.session;
      if (session && session.user) {
        console.log('[Auth Hook]: Active Supabase session found for user:', session.user.email);
        const authUser: User = {
          id: session.user.id,
          email: session.user.email || '',
        };
        localStorage.setItem('rag_token', session.access_token);
        localStorage.setItem('rag_user', JSON.stringify(authUser));
        setUser(authUser);
      }
      setLoading(false);
    }).catch((err) => {
      console.warn('[Auth Hook]: Exception restoring Supabase session:', err);
      setLoading(false);
    });

    // 3. Set up onAuthStateChange listener to handle OAuth redirect & session events
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      console.log(`[Auth Listener]: Event "${event}" triggered. Location: ${window.location.href}`);
      if (session && session.user) {
        const authUser: User = {
          id: session.user.id,
          email: session.user.email || '',
        };
        localStorage.setItem('rag_token', session.access_token);
        localStorage.setItem('rag_user', JSON.stringify(authUser));
        setUser(authUser);

        // Handle specific events (e.g. redirect to /dashboard upon returning from Google OAuth)
        if (event === 'SIGNED_IN' || event === 'INITIAL_SESSION') {
          if (window.location.pathname === '/' || window.location.pathname === '/login') {
            navigate('/dashboard');
          }
        }
      } else if (event === 'SIGNED_OUT') {
        localStorage.removeItem('rag_token');
        localStorage.removeItem('rag_user');
        setUser(null);
      }
      setLoading(false);
    });

    return () => {
      subscription.unsubscribe();
    };
  }, [navigate]);

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
        if (response.session) {
          localStorage.setItem('rag_token', response.session.access_token);
          localStorage.setItem('rag_user', JSON.stringify(response.user));
          setUser(response.user);
        } else {
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
    supabase.auth.signOut().catch(() => {});
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
