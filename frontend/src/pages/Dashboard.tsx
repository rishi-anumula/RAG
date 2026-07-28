import React, { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import dashboardService from '../services/dashboardService';
import type { DashboardMetrics } from '../types';
import { 
  FileText, 
  MessageSquare, 
  HardDrive, 
  Plus, 
  MessageCircle, 
  Clock, 
  ExternalLink,
  ChevronRight,
  TrendingUp
} from 'lucide-react';

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const data = await dashboardService.getMetrics();
        setMetrics(data);
        setError(null);
      } catch (err: any) {
        console.warn('Failed to fetch dashboard metrics, using fallback metrics:', err);
        setMetrics({
          total_pdfs: 0,
          total_conversations: 0,
          storage_usage_bytes: 0,
          recent_uploads: [],
          recent_chats: []
        });
      } finally {
        setLoading(false);
      }
    };
    fetchMetrics();
  }, []);

  const formatBytes = (bytes: number, decimals = 2) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <svg className="animate-spin h-10 w-10 text-brand-500" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
        <span className="text-dark-400 text-sm font-medium">Fetching workspace metrics...</span>
      </div>
    );
  }

  if (error || !metrics) {
    return (
      <div className="glass rounded-2xl p-8 max-w-lg mx-auto text-center border-red-500/20">
        <h3 className="text-xl font-bold text-red-400 mb-2">Error Loading Dashboard</h3>
        <p className="text-dark-400 mb-6">{error || 'An unexpected error occurred.'}</p>
        <button 
          onClick={() => window.location.reload()}
          className="bg-brand-600 hover:bg-brand-500 text-white px-5 py-2.5 rounded-xl text-sm font-semibold transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  // Calculate percentage of 100MB storage limit
  const storageLimit = 100 * 1024 * 1024; // 100 MB
  const storagePercentage = Math.min(100, Math.round((metrics.storage_usage_bytes / storageLimit) * 100));

  return (
    <div className="space-y-8">
      {/* Title */}
      <div>
        <h1 className="text-3xl font-extrabold text-white tracking-tight">Dashboard</h1>
        <p className="text-dark-400 text-sm mt-1">Quick summary of your knowledge base environment</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Total Documents Card */}
        <div className="glass-card glass-card-hover p-6 rounded-2xl flex items-center justify-between">
          <div className="space-y-2">
            <p className="text-xs font-semibold tracking-wider text-dark-500 uppercase">Total PDFs</p>
            <h3 className="text-4xl font-extrabold text-white">{metrics.total_pdfs}</h3>
            <span className="inline-flex items-center text-xs text-brand-400 font-medium space-x-1">
              <TrendingUp className="h-3.5 w-3.5" />
              <span>Available sources</span>
            </span>
          </div>
          <div className="h-12 w-12 rounded-xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center text-brand-400">
            <FileText className="h-6 w-6" />
          </div>
        </div>

        {/* Chats Card */}
        <div className="glass-card glass-card-hover p-6 rounded-2xl flex items-center justify-between">
          <div className="space-y-2">
            <p className="text-xs font-semibold tracking-wider text-dark-500 uppercase">Conversations</p>
            <h3 className="text-4xl font-extrabold text-white">{metrics.total_conversations}</h3>
            <span className="inline-flex items-center text-xs text-purple-400 font-medium space-x-1">
              <MessageCircle className="h-3.5 w-3.5" />
              <span>Interactive threads</span>
            </span>
          </div>
          <div className="h-12 w-12 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
            <MessageSquare className="h-6 w-6" />
          </div>
        </div>

        {/* Storage Card */}
        <div className="glass-card glass-card-hover p-6 rounded-2xl flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4">
            <div className="space-y-1">
              <p className="text-xs font-semibold tracking-wider text-dark-500 uppercase">Storage Used</p>
              <h3 className="text-2xl font-extrabold text-white">{formatBytes(metrics.storage_usage_bytes)}</h3>
            </div>
            <div className="h-12 w-12 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
              <HardDrive className="h-6 w-6" />
            </div>
          </div>
          {/* Progress bar */}
          <div className="space-y-1.5">
            <div className="w-full bg-dark-800 rounded-full h-2">
              <div 
                className="bg-gradient-to-r from-brand-500 to-cyan-500 h-2 rounded-full transition-all duration-500" 
                style={{ width: `${storagePercentage}%` }}
              ></div>
            </div>
            <div className="flex justify-between text-xs text-dark-500 font-medium">
              <span>{storagePercentage}% full</span>
              <span>100 MB Limit</span>
            </div>
          </div>
        </div>

      </div>

      {/* Main Panel layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Side: Recent Lists (2 cols) */}
        <div className="lg:col-span-2 space-y-8">
          
          {/* Recent Uploads */}
          <div className="glass rounded-2xl p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-dark-800 pb-4">
              <div className="flex items-center space-x-2">
                <Clock className="h-5 w-5 text-dark-400" />
                <h3 className="text-lg font-bold text-white">Recent Uploads</h3>
              </div>
              <Link to="/documents" className="text-xs text-brand-400 hover:text-brand-300 font-medium inline-flex items-center space-x-1">
                <span>View all</span>
                <ChevronRight className="h-3 w-3" />
              </Link>
            </div>
            
            {metrics.recent_uploads.length === 0 ? (
              <div className="text-center py-6 text-dark-500 text-sm">
                No documents uploaded yet.
              </div>
            ) : (
              <div className="divide-y divide-dark-800">
                {metrics.recent_uploads.map((doc) => (
                  <div key={doc.id} className="py-3 flex items-center justify-between first:pt-0 last:pb-0">
                    <div className="min-w-0 pr-4">
                      <p className="text-sm font-semibold text-dark-200 truncate">{doc.name}</p>
                      <p className="text-xs text-dark-500 mt-0.5">{formatBytes(doc.size)} • {new Date(doc.created_at).toLocaleDateString()}</p>
                    </div>
                    <div>
                      <span className={`
                        px-2.5 py-0.5 rounded-full text-xs font-semibold tracking-wide
                        ${doc.status === 'processed' ? 'bg-green-500/10 text-green-400' : ''}
                        ${doc.status === 'processing' ? 'bg-brand-500/10 text-brand-400 animate-pulse' : ''}
                        ${doc.status === 'uploaded' ? 'bg-yellow-500/10 text-yellow-400' : ''}
                        ${doc.status === 'failed' ? 'bg-red-500/10 text-red-400' : ''}
                      `}>
                        {doc.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Recent Conversations */}
          <div className="glass rounded-2xl p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-dark-800 pb-4">
              <div className="flex items-center space-x-2">
                <MessageSquare className="h-5 w-5 text-dark-400" />
                <h3 className="text-lg font-bold text-white">Recent Chats</h3>
              </div>
              <Link to="/chat" className="text-xs text-brand-400 hover:text-brand-300 font-medium inline-flex items-center space-x-1">
                <span>Open chat room</span>
                <ChevronRight className="h-3 w-3" />
              </Link>
            </div>
            
            {metrics.recent_chats.length === 0 ? (
              <div className="text-center py-6 text-dark-500 text-sm">
                No active conversations. Start a new chat to ask questions.
              </div>
            ) : (
              <div className="divide-y divide-dark-800">
                {metrics.recent_chats.map((chat) => (
                  <div key={chat.id} className="py-3.5 flex items-center justify-between first:pt-0 last:pb-0">
                    <div className="min-w-0 pr-4">
                      <p className="text-sm font-semibold text-dark-200 truncate">{chat.title}</p>
                      <p className="text-xs text-dark-500 mt-0.5">Last active: {new Date(chat.updated_at).toLocaleString()}</p>
                    </div>
                    <button 
                      onClick={() => navigate(`/chat?conv_id=${chat.id}`)}
                      className="p-1.5 hover:bg-dark-800 border border-dark-800 hover:border-brand-500/30 rounded-lg text-dark-400 hover:text-brand-400 transition-colors"
                    >
                      <ExternalLink className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

        </div>

        {/* Right Side: Quick Action Panel (1 col) */}
        <div className="space-y-6">
          <div className="glass rounded-2xl p-6 space-y-4">
            <h3 className="text-lg font-bold text-white border-b border-dark-800 pb-3">Quick Actions</h3>
            
            <button
              onClick={() => navigate('/documents')}
              className="w-full flex items-center space-x-3 p-3.5 bg-dark-900 border border-dark-800 hover:border-brand-500/40 rounded-xl hover:bg-dark-800/30 transition-all duration-200 text-left group"
            >
              <div className="h-10 w-10 rounded-lg bg-brand-500/10 flex items-center justify-center text-brand-400 shrink-0 group-hover:scale-105 transition-transform">
                <Plus className="h-5 w-5" />
              </div>
              <div>
                <p className="text-sm font-semibold text-dark-200">Upload PDF</p>
                <p className="text-xs text-dark-500 mt-0.5">Index new reference materials</p>
              </div>
            </button>

            <button
              onClick={() => navigate('/chat')}
              className="w-full flex items-center space-x-3 p-3.5 bg-dark-900 border border-dark-800 hover:border-purple-500/40 rounded-xl hover:bg-dark-800/30 transition-all duration-200 text-left group"
            >
              <div className="h-10 w-10 rounded-lg bg-purple-500/10 flex items-center justify-center text-purple-400 shrink-0 group-hover:scale-105 transition-transform">
                <MessageCircle className="h-5 w-5" />
              </div>
              <div>
                <p className="text-sm font-semibold text-dark-200">New Question</p>
                <p className="text-xs text-dark-500 mt-0.5">Ask questions about PDFs</p>
              </div>
            </button>
          </div>

          {/* RAG pipeline explainer */}
          <div className="glass rounded-2xl p-6 bg-gradient-to-br from-brand-600/5 to-cyan-500/5 border border-brand-500/10">
            <h4 className="text-sm font-bold text-white mb-2">How it works</h4>
            <p className="text-xs text-dark-400 leading-relaxed">
              When you upload a PDF, we extract its text, segment it into overlap chunks of 1,000 characters, generate vector representations using a Sentence-Transformer model, and index them.
              When chatting, we search for matching sources and query Gemini to answer strictly based on them.
            </p>
          </div>
        </div>

      </div>
    </div>
  );
};
export default Dashboard;
