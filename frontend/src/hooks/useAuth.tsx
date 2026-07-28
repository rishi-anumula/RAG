import React, { createContext, useContext, useState, useEffect } from 'react';
import type { User, LoginCredentials } from '../types';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  signup: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const guestUser: User = { 
      id: '00000000-0000-0000-0000-000000000000', 
      email: 'guest@example.com' 
    };
    localStorage.setItem('rag_token', 'mock-guest-token');
    localStorage.setItem('rag_user', JSON.stringify(guestUser));
    setUser(guestUser);
    setLoading(false);
  }, []);

  const login = async (_credentials: LoginCredentials) => {
    return Promise.resolve();
  };

  const signup = async (_credentials: LoginCredentials) => {
    return Promise.resolve();
  };

  const logout = () => {
    // No-op in guest mode
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout }}>
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
