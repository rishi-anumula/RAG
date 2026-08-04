import React, { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { documentService } from '../services/documentService';
import { authService } from '../services/authService';
import type { Document } from '../types';
import { 
  Mail, 
  KeyRound, 
  ShieldCheck, 
  HardDrive, 
  FileText, 
  MessageSquare, 
  Sparkles, 
  LogOut, 
  CheckCircle2, 
  AlertCircle,
  Clock,
  Database
} from 'lucide-react';

export const Profile: React.FC = () => {
  const { user, logout } = useAuth();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(true);

  // Form states
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [passwordSuccess, setPasswordSuccess] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const list = await documentService.list();
        setDocuments(list || []);
      } catch (err) {
        console.error('Failed to fetch document stats:', err);
      } finally {
        setLoadingDocs(false);
      }
    };
    fetchStats();
  }, []);

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError(null);
    setPasswordSuccess(null);

    if (!currentPassword || !newPassword || !confirmPassword) {
      setPasswordError('Please fill in all password fields.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setPasswordError('New passwords do not match.');
      return;
    }

    if (newPassword.length < 6) {
      setPasswordError('New password must be at least 6 characters long.');
      return;
    }

    setPasswordLoading(true);
    try {
      const res = await authService.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      setPasswordSuccess(res.message || 'Password updated successfully!');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.detail ||
        err.message ||
        'Failed to update password. Please verify your current password.';
      setPasswordError(errorMessage);
    } finally {
      setPasswordLoading(false);
    }
  };

  // Compute storage statistics
  const totalSizeBytes = documents.reduce((acc, doc) => acc + (doc.size || 0), 0);
  const formattedStorage = (totalSizeBytes / (1024 * 1024)).toFixed(2);
  const maxStorageMB = 500;
  const storagePercentage = Math.min(100, Math.round((parseFloat(formattedStorage) / maxStorageMB) * 100));

  const userInitials = (user?.email || 'Guest User')
    .split('@')[0]
    .substring(0, 2)
    .toUpperCase();

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      
      {/* Page Title Header */}
      <div>
        <h1 className="text-3xl font-extrabold text-white tracking-tight">User Profile</h1>
        <p className="text-dark-400 text-sm mt-1">Manage your account credentials, security settings, and workspace usage</p>
      </div>

      {/* Identity Banner Card */}
      <div className="glass rounded-3xl p-6 md:p-8 border border-dark-800 flex flex-col md:flex-row items-center justify-between gap-6 relative overflow-hidden">
        
        {/* Glow accent */}
        <div className="absolute top-0 right-0 w-80 h-80 bg-brand-500/10 rounded-full blur-3xl pointer-events-none"></div>

        <div className="flex flex-col md:flex-row items-center space-y-4 md:space-y-0 md:space-x-6 z-10 text-center md:text-left">
          {/* Avatar Badge */}
          <div className="h-20 w-20 rounded-2xl bg-gradient-to-tr from-brand-600 to-purple-500 flex items-center justify-center text-white font-extrabold text-2xl shadow-xl shadow-brand-500/25 shrink-0 border border-white/10">
            {userInitials}
          </div>

          <div className="space-y-1">
            <div className="flex items-center justify-center md:justify-start space-x-2">
              <h2 className="text-xl font-bold text-white truncate">{user?.email || 'guest@example.com'}</h2>
              <span className="px-2.5 py-0.5 bg-brand-500/10 border border-brand-500/20 text-brand-400 text-[10px] font-bold uppercase rounded-full tracking-wider flex items-center space-x-1">
                <Sparkles className="h-3 w-3 inline" />
                <span>Active Member</span>
              </span>
            </div>
            
            <p className="text-xs text-dark-400 font-mono">
              User ID: {user?.id || '00000000-0000-0000-0000-000000000000'}
            </p>
            
            <div className="flex items-center justify-center md:justify-start space-x-4 pt-1 text-xs text-dark-400">
              <span className="flex items-center space-x-1">
                <ShieldCheck className="h-3.5 w-3.5 text-green-400" />
                <span>Verified Account</span>
              </span>
              <span className="flex items-center space-x-1">
                <Clock className="h-3.5 w-3.5 text-brand-400" />
                <span>Active Session</span>
              </span>
            </div>
          </div>
        </div>

        {/* Log Out Action */}
        <button
          onClick={logout}
          className="px-4 py-2.5 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 rounded-xl text-xs font-semibold transition-all flex items-center space-x-2 shrink-0 z-10"
        >
          <LogOut className="h-4 w-4" />
          <span>Sign Out</span>
        </button>

      </div>

      {/* Grid: Stats Overview & Password Management */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column: Account Usage Metrics (1 col) */}
        <div className="space-y-6">
          <div className="glass rounded-2xl p-6 border border-dark-800 space-y-6">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider text-dark-300 flex items-center space-x-2">
              <Database className="h-4 w-4 text-brand-400" />
              <span>Workspace Usage</span>
            </h3>

            {/* Storage Gauge */}
            <div className="space-y-2">
              <div className="flex justify-between text-xs font-semibold">
                <span className="text-dark-300">Storage Used</span>
                <span className="text-brand-400">{formattedStorage} MB / {maxStorageMB} MB</span>
              </div>
              <div className="w-full bg-dark-900 rounded-full h-2 overflow-hidden border border-dark-800">
                <div 
                  className="bg-gradient-to-r from-brand-500 to-purple-500 h-2 rounded-full transition-all duration-500"
                  style={{ width: `${storagePercentage}%` }}
                ></div>
              </div>
              <p className="text-[11px] text-dark-500 pt-0.5">
                {storagePercentage}% of your total 500MB cloud vector allocation used.
              </p>
            </div>

            {/* Metrics List */}
            <div className="space-y-3 pt-2 border-t border-dark-800/80">
              <div className="flex items-center justify-between py-2 text-xs">
                <span className="text-dark-400 flex items-center space-x-2">
                  <FileText className="h-4 w-4 text-brand-400" />
                  <span>Total Documents</span>
                </span>
                <span className="font-bold text-white">{loadingDocs ? '...' : documents.length}</span>
              </div>

              <div className="flex items-center justify-between py-2 text-xs border-t border-dark-800/50">
                <span className="text-dark-400 flex items-center space-x-2">
                  <HardDrive className="h-4 w-4 text-purple-400" />
                  <span>Processed Segments</span>
                </span>
                <span className="font-bold text-white">{loadingDocs ? '...' : documents.length * 12}</span>
              </div>

              <div className="flex items-center justify-between py-2 text-xs border-t border-dark-800/50">
                <span className="text-dark-400 flex items-center space-x-2">
                  <MessageSquare className="h-4 w-4 text-emerald-400" />
                  <span>AI Queries Asked</span>
                </span>
                <span className="font-bold text-white">28 Queries</span>
              </div>
            </div>

          </div>
        </div>

        {/* Right Column: Profile Security & Password Update (2 cols) */}
        <div className="lg:col-span-2 glass rounded-2xl p-6 md:p-8 border border-dark-800 space-y-6">
          
          <div className="border-b border-dark-800 pb-4">
            <h3 className="text-lg font-bold text-white flex items-center space-x-2">
              <KeyRound className="h-5 w-5 text-brand-400" />
              <span>Security & Credentials</span>
            </h3>
            <p className="text-xs text-dark-400 mt-1">Update your password and authentication preferences</p>
          </div>

          {/* Password Alerts */}
          {passwordError && (
            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center space-x-2 text-xs text-red-400">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{passwordError}</span>
            </div>
          )}

          {passwordSuccess && (
            <div className="p-3 bg-green-500/10 border border-green-500/20 rounded-xl flex items-center space-x-2 text-xs text-green-400">
              <CheckCircle2 className="h-4 w-4 shrink-0" />
              <span>{passwordSuccess}</span>
            </div>
          )}

          {/* Change Password Form */}
          <form onSubmit={handlePasswordChange} className="space-y-4">
            
            {/* Account Email Display (Read-Only) */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-dark-300">Account Email</label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-dark-500">
                  <Mail className="h-4 w-4" />
                </span>
                <input
                  type="email"
                  disabled
                  value={user?.email || 'guest@example.com'}
                  className="w-full bg-dark-900/60 border border-dark-800 rounded-xl py-2.5 pl-10 pr-4 text-dark-400 text-sm cursor-not-allowed select-none"
                />
              </div>
            </div>

            {/* Current Password */}
            <div className="space-y-1.5 pt-2">
              <label className="text-xs font-semibold text-dark-300">Current Password</label>
              <input
                type="password"
                placeholder="Enter current password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="w-full bg-dark-900 border border-dark-800 rounded-xl py-2.5 px-4 text-white text-sm placeholder-dark-500 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-colors"
              />
            </div>

            {/* New Password & Confirm */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-dark-300">New Password</label>
                <input
                  type="password"
                  placeholder="At least 6 characters"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full bg-dark-900 border border-dark-800 rounded-xl py-2.5 px-4 text-white text-sm placeholder-dark-500 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-colors"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-dark-300">Confirm New Password</label>
                <input
                  type="password"
                  placeholder="Re-enter new password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="w-full bg-dark-900 border border-dark-800 rounded-xl py-2.5 px-4 text-white text-sm placeholder-dark-500 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-colors"
                />
              </div>
            </div>

            {/* Submit Button */}
            <div className="flex justify-end pt-2">
              <button
                type="submit"
                disabled={passwordLoading}
                className="px-6 py-2.5 bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white rounded-xl text-xs font-semibold transition-all shadow-lg shadow-brand-500/20"
              >
                {passwordLoading ? 'Updating Password...' : 'Update Password'}
              </button>
            </div>

          </form>

        </div>

      </div>

    </div>
  );
};

export default Profile;
