import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { 
  LayoutDashboard, 
  FileText, 
  MessageSquare, 
  Settings as SettingsIcon, 
  BookOpen,
  Menu,
  X,
  LogOut
} from 'lucide-react';

export const DashboardLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const location = useLocation();
  const { user, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = React.useState(false);

  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Documents', href: '/documents', icon: FileText },
    { name: 'Chat', href: '/chat', icon: MessageSquare },
    { name: 'Settings', href: '/settings', icon: SettingsIcon },
  ];

  const isActive = (path: string) => {
    return location.pathname === path;
  };

  return (
    <div className="min-h-screen bg-dark-950 text-dark-100 flex flex-col md:flex-row">
      
      {/* Mobile Top Navbar */}
      <header className="md:hidden glass h-16 px-4 flex items-center justify-between z-50 sticky top-0">
        <Link to="/dashboard" className="flex items-center space-x-2 text-brand-400 font-bold text-lg">
          <BookOpen className="h-6 w-6" />
          <span>RAG.ai</span>
        </Link>
        <button 
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="p-2 hover:bg-dark-800 rounded-md focus:outline-none"
        >
          {sidebarOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
      </header>

      {/* Sidebar Navigation */}
      <aside className={`
        fixed inset-y-0 left-0 transform ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        md:relative md:translate-x-0 transition-transform duration-300 ease-in-out
        w-64 bg-dark-900/80 border-r border-dark-800 flex flex-col justify-between z-40
        ${sidebarOpen ? 'pt-20' : 'pt-0'} md:pt-0
      `}>
        <div className="flex-1 px-4 py-6 flex flex-col">
          {/* Logo */}
          <div className="hidden md:flex items-center space-x-3 mb-8 px-2">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-brand-600 to-brand-400 flex items-center justify-center shadow-lg shadow-brand-500/20">
              <BookOpen className="h-5 w-5 text-white" />
            </div>
            <span className="font-extrabold text-xl bg-gradient-to-r from-white to-dark-300 bg-clip-text text-transparent">
              RAG Search
            </span>
          </div>

          {/* Navigation Links */}
          <nav className="space-y-1.5 flex-1">
            {navigation.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.href);
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  onClick={() => setSidebarOpen(false)}
                  className={`
                    flex items-center space-x-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200
                    ${active 
                      ? 'bg-brand-600/10 text-brand-400 border border-brand-500/20 shadow-lg shadow-brand-500/5' 
                      : 'text-dark-400 hover:bg-dark-800/50 hover:text-dark-100 border border-transparent'
                    }
                  `}
                >
                  <Icon className={`h-5 w-5 ${active ? 'text-brand-400' : 'text-dark-400'}`} />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* User Profile & Log Out */}
        <div className="p-4 border-t border-dark-800">
          <div className="flex items-center justify-between px-2 py-1">
            <div className="overflow-hidden pr-2">
              <p className="text-[10px] uppercase font-bold text-dark-500 tracking-wider">Active Profile</p>
              <p className="text-xs font-semibold text-brand-400 truncate" title={user?.email || 'Guest User'}>
                {user?.email || 'guest@example.com'}
              </p>
            </div>
            <button 
              onClick={logout} 
              className="p-2 hover:bg-red-500/10 text-dark-400 hover:text-red-400 rounded-xl transition-colors"
              title="Log Out"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        <div className="flex-1 px-4 py-8 md:p-8 max-w-7xl w-full mx-auto">
          {children}
        </div>
      </main>

    </div>
  );
};
export default DashboardLayout;
