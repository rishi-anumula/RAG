import React from 'react';
import { Link } from 'react-router-dom';
import { 
  BookOpen, 
  Database, 
  Cpu, 
  ShieldCheck, 
  ArrowRight, 
  Sparkles, 
  GitBranch, 
  FileText
} from 'lucide-react';

export const LandingPage: React.FC = () => {
  const steps = [
    {
      title: "PDF Upload",
      desc: "Drag and drop research papers or reports. Files are uploaded securely to Supabase Storage caches.",
      icon: FileText,
      color: "text-brand-400 bg-brand-500/10 border-brand-500/20"
    },
    {
      title: "Chunking & Hashing",
      desc: "Documents are split into 1,000-character pages with 200-character overlaps to isolate logical semantic blocks.",
      icon: GitBranch,
      color: "text-purple-400 bg-purple-500/10 border-purple-500/20"
    },
    {
      title: "Local Embeddings",
      desc: "MiniLM-L6 transformers generate 384-dimensional vector hashes stored directly inside a local ChromaDB instance.",
      icon: Database,
      color: "text-cyan-400 bg-cyan-500/10 border-cyan-500/20"
    },
    {
      title: "Gemini Synthesis",
      desc: "We perform cosine similarity lookups, attach matching citations, and invoke Gemini to answer solely from context.",
      icon: Cpu,
      color: "text-amber-400 bg-amber-500/10 border-amber-500/20"
    }
  ];

  return (
    <div className="min-h-screen bg-dark-950 text-dark-100 flex flex-col relative overflow-hidden">
      
      {/* Decorative Blur Orbs */}
      <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-brand-600/5 rounded-full blur-[120px] pointer-events-none"></div>
      <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-cyan-600/5 rounded-full blur-[120px] pointer-events-none"></div>

      {/* Header */}
      <header className="glass h-16 sticky top-0 z-50 flex items-center px-4 md:px-8 border-b border-dark-800/80">
        <div className="max-w-7xl w-full mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-2.5 text-white font-extrabold text-lg">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-tr from-brand-600 to-brand-400 flex items-center justify-center shadow-lg shadow-brand-500/10">
              <BookOpen className="h-4 w-4 text-white" />
            </div>
            <span>RAG Search</span>
          </div>

          <div className="flex items-center space-x-4">
            <Link to="/login" className="text-xs font-semibold text-dark-300 hover:text-white transition-colors">
              Sign In
            </Link>
            <Link 
              to="/signup" 
              className="px-3.5 py-1.5 bg-brand-600 hover:bg-brand-500 text-white rounded-lg text-xs font-semibold shadow-md shadow-brand-600/10 transition-colors"
            >
              Get Started
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="flex-1 flex flex-col items-center justify-center text-center px-4 max-w-4xl mx-auto py-20 relative z-10 space-y-8">
        
        {/* Animated Badge */}
        <div className="inline-flex items-center space-x-1.5 px-3 py-1 bg-brand-600/10 border border-brand-500/20 text-brand-400 rounded-full text-xs font-bold animate-pulse-slow">
          <Sparkles className="h-3.5 w-3.5" />
          <span>Vector Search RAG Pipeline</span>
        </div>

        {/* Hero Title */}
        <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white leading-tight">
          Search your local PDF knowledge base with{' '}
          <span className="bg-gradient-to-r from-brand-400 to-cyan-400 bg-clip-text text-transparent">
            Gemini
          </span>
        </h1>

        {/* Hero Subtitle */}
        <p className="text-sm sm:text-lg text-dark-400 max-w-2xl leading-relaxed">
          Upload PDF documents, extract vector segments page-by-page, and ask complex questions. 
          Answers are generated strictly from your documents with inline citation pages.
        </p>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center items-center pt-4">
          <Link 
            to="/signup" 
            className="w-full sm:w-auto px-6 py-3 bg-brand-600 hover:bg-brand-500 text-white rounded-xl font-semibold text-sm shadow-xl shadow-brand-600/25 transition-all flex items-center justify-center space-x-2 group"
          >
            <span>Register Workspace</span>
            <ArrowRight className="h-4 w-4 group-hover:translate-x-1 transition-transform" />
          </Link>
          <Link 
            to="/login" 
            className="w-full sm:w-auto px-6 py-3 bg-dark-900 border border-dark-850 hover:border-brand-500/30 text-dark-100 rounded-xl font-semibold text-sm transition-all"
          >
            Open Dashboard
          </Link>
        </div>

      </section>

      {/* RAG Steps Section */}
      <section className="bg-dark-900/30 border-t border-dark-900 py-20 px-4">
        <div className="max-w-6xl mx-auto space-y-12">
          
          <div className="text-center space-y-2">
            <h2 className="text-2xl sm:text-3xl font-extrabold text-white">Full-Stack RAG Architecture</h2>
            <p className="text-dark-500 text-xs sm:text-sm">End-to-end vector indexing and citation matching workflow</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {steps.map((step, idx) => {
              const Icon = step.icon;
              return (
                <div key={idx} className="glass-card glass-card-hover p-6 rounded-2xl space-y-4">
                  <div className={`h-11 w-11 rounded-lg flex items-center justify-center border shrink-0 ${step.color}`}>
                    <Icon className="h-5 w-5" />
                  </div>
                  <h3 className="text-sm font-bold text-white">{step.title}</h3>
                  <p className="text-xs text-dark-400 leading-relaxed">{step.desc}</p>
                </div>
              );
            })}
          </div>

        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-dark-900 h-16 flex items-center px-4 md:px-8 bg-dark-950/80">
        <div className="max-w-7xl w-full mx-auto flex flex-col sm:flex-row items-center justify-between text-xs text-dark-500 space-y-2 sm:space-y-0">
          <span>&copy; {new Date().getFullYear()} RAG.ai Knowledge Search Engine. All rights reserved.</span>
          <div className="flex space-x-4">
            <span className="flex items-center space-x-1">
              <ShieldCheck className="h-4 w-4 text-emerald-400" />
              <span>Supabase Authentication</span>
            </span>
          </div>
        </div>
      </footer>

    </div>
  );
};
export default LandingPage;
