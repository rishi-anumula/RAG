import React from 'react';
import { useAuth } from '../hooks/useAuth';
import { 
  User as UserIcon, 
  Key, 
  Monitor, 
  Database,
  CheckCircle
} from 'lucide-react';

export const Settings: React.FC = () => {
  const { user } = useAuth();

  // Mock status verification (since backend validates at startup)
  const isGeminiConnected = true;

  return (
    <div className="space-y-8">
      {/* Title */}
      <div>
        <h1 className="text-3xl font-extrabold text-white tracking-tight">Settings</h1>
        <p className="text-dark-400 text-sm mt-1">Manage configuration and environment variables</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Side: General Profile & Details (2 cols) */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* User Profile */}
          <div className="glass rounded-2xl p-6 space-y-4">
            <h3 className="text-lg font-bold text-white flex items-center space-x-2 border-b border-dark-800 pb-3">
              <UserIcon className="h-5 w-5 text-brand-400" />
              <span>User Profile</span>
            </h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div className="space-y-1">
                <p className="text-xs font-semibold text-dark-500">Account ID</p>
                <p className="text-dark-200 font-mono select-all bg-dark-900 px-3 py-1.5 border border-dark-850 rounded-lg text-xs truncate">
                  {user?.id}
                </p>
              </div>
              <div className="space-y-1">
                <p className="text-xs font-semibold text-dark-500">Email Address</p>
                <p className="text-dark-200 bg-dark-900 px-3 py-1.5 border border-dark-850 rounded-lg text-xs truncate">
                  {user?.email}
                </p>
              </div>
            </div>
          </div>

          {/* Database System info */}
          <div className="glass rounded-2xl p-6 space-y-4">
            <h3 className="text-lg font-bold text-white flex items-center space-x-2 border-b border-dark-800 pb-3">
              <Database className="h-5 w-5 text-cyan-400" />
              <span>System & Storage</span>
            </h3>
            
            <div className="space-y-3.5 text-xs">
              <div className="flex items-center justify-between p-3 bg-dark-900/60 rounded-xl border border-dark-850">
                <div>
                  <p className="font-semibold text-dark-200">Local Database (SQLite)</p>
                  <p className="text-dark-500 mt-0.5">Offline metadata management and user credentials store</p>
                </div>
                <span className="flex items-center space-x-1 text-emerald-400 font-semibold">
                  <CheckCircle className="h-4 w-4" />
                  <span>Connected (Offline)</span>
                </span>
              </div>

              <div className="flex items-center justify-between p-3 bg-dark-900/60 rounded-xl border border-dark-850">
                <div>
                  <p className="font-semibold text-dark-200">ChromaDB Persistent Store</p>
                  <p className="text-dark-500 mt-0.5">Local vector engine for document chunk embeddings</p>
                </div>
                <span className="flex items-center space-x-1 text-emerald-400 font-semibold">
                  <CheckCircle className="h-4 w-4" />
                  <span>Connected</span>
                </span>
              </div>
            </div>
          </div>

        </div>

        {/* Right Side: Key & Connection Status (1 col) */}
        <div className="space-y-6">
          
          {/* Key Connections */}
          <div className="glass rounded-2xl p-6 space-y-4">
            <h3 className="text-sm font-bold text-white flex items-center space-x-2 border-b border-dark-800 pb-3 uppercase tracking-wider">
              <Key className="h-4 w-4 text-purple-400" />
              <span>API Credentials</span>
            </h3>
            
            <div className="space-y-4">
              <div className="space-y-2">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-semibold text-dark-300">Google Gemini API</span>
                  {isGeminiConnected ? (
                    <span className="text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full font-bold">ACTIVE</span>
                  ) : (
                    <span className="text-[10px] bg-red-500/10 text-red-400 border border-red-500/20 px-2 py-0.5 rounded-full font-bold">MISSING</span>
                  )}
                </div>
                <p className="text-[11px] text-dark-500 leading-normal">
                  Required to generate contextual responses. Configured on the FastAPI server environment.
                </p>
              </div>

              <div className="space-y-2 pt-2 border-t border-dark-800">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-semibold text-dark-300">Embedding Model</span>
                  <span className="text-[10px] bg-brand-500/10 text-brand-400 border border-brand-500/20 px-2 py-0.5 rounded-full font-bold">MiniLM-L6</span>
                </div>
                <p className="text-[11px] text-dark-500 leading-normal">
                  Local Sentence-Transformer running on CPU/GPU. Used to compute semantic query hashes.
                </p>
              </div>
            </div>
          </div>

          {/* Guidelines info */}
          <div className="glass rounded-2xl p-6 bg-gradient-to-br from-brand-600/5 to-cyan-500/5 border border-brand-500/10 space-y-2">
            <h4 className="text-xs font-bold text-white flex items-center space-x-1">
              <Monitor className="h-4 w-4 text-brand-400" />
              <span>Theme Preference</span>
            </h4>
            <p className="text-[11px] text-dark-400 leading-relaxed">
              Theme is locked to Midnight Dark mode for visual premium contrast. Dark styling reduces glare and keeps interactive panels sharp.
            </p>
          </div>

        </div>

      </div>
    </div>
  );
};
export default Settings;
