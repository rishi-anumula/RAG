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
  FileText,
  Search,
  Zap,
  Lock,
  Layers
} from 'lucide-react';

export const LandingPage: React.FC = () => {
  const features = [
    {
      title: "PDF Upload & Intelligent Chunking",
      desc: "Drag and drop research papers, manuals, or documents. Text is automatically segmented into precise 1,000-character blocks with overlapping margins for complete context preservation.",
      icon: FileText,
      color: "text-brand-400 bg-brand-500/10 border-brand-500/20"
    },
    {
      title: "Local Vector Hashing",
      desc: "Sentence-Transformer models generate 384-dimensional dense embeddings stored in a high-speed ChromaDB vector store for instant similarity retrieval.",
      icon: GitBranch,
      color: "text-purple-400 bg-purple-500/10 border-purple-500/20"
    },
    {
      title: "Semantic Context Retrieval",
      desc: "When you ask a question, cosine similarity algorithms fetch the exact document passages and page numbers relevant to your query.",
      icon: Database,
      color: "text-cyan-400 bg-cyan-500/10 border-cyan-500/20"
    },
    {
      title: "Gemini AI Synthesis with Citations",
      desc: "Google Gemini constructs precise answers strictly bounded by your document data, providing inline page citations for complete verification.",
      icon: Cpu,
      color: "text-amber-400 bg-amber-500/10 border-amber-500/20"
    }
  ];

  return (
    <div className="min-h-screen bg-dark-950 text-dark-100 flex flex-col relative overflow-hidden font-sans">
      
      {/* Decorative Gradient Orbs */}
      <div className="absolute top-0 left-1/4 w-[600px] h-[600px] bg-brand-600/10 rounded-full blur-[140px] pointer-events-none animate-pulse-slow"></div>
      <div className="absolute bottom-10 right-1/4 w-[500px] h-[500px] bg-cyan-500/10 rounded-full blur-[130px] pointer-events-none"></div>

      {/* Top Navbar */}
      <header className="glass h-16 sticky top-0 z-50 flex items-center px-4 md:px-8 border-b border-dark-800/80">
        <div className="max-w-7xl w-full mx-auto flex items-center justify-between">
          
          {/* Logo Brand */}
          <div className="flex items-center space-x-2.5 text-white font-extrabold text-lg tracking-tight">
            <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-brand-600 to-brand-400 flex items-center justify-center shadow-lg shadow-brand-500/20">
              <BookOpen className="h-5 w-5 text-white" />
            </div>
            <span className="bg-gradient-to-r from-white via-dark-100 to-dark-300 bg-clip-text text-transparent">
              RAG Search
            </span>
          </div>

          {/* Navigation Links */}
          <div className="flex items-center space-x-3 sm:space-x-4">
            <Link 
              to="/login" 
              className="px-4 py-2 text-xs font-semibold text-dark-300 hover:text-white transition-colors"
            >
              Sign In
            </Link>
            <Link 
              to="/login" 
              className="px-4 py-2 bg-brand-600 hover:bg-brand-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-brand-600/25 transition-all flex items-center space-x-1.5"
            >
              <span>Get Started</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>

        </div>
      </header>

      {/* Main Hero Section */}
      <section className="flex-1 flex flex-col items-center justify-center text-center px-4 max-w-4xl mx-auto py-16 sm:py-24 relative z-10 space-y-8">
        
        {/* Top Tagline Badge */}
        <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 bg-brand-600/10 border border-brand-500/20 text-brand-400 rounded-full text-xs font-bold shadow-sm">
          <Sparkles className="h-4 w-4 text-brand-400 animate-spin-slow" />
          <span>Next-Generation Retrieval-Augmented Generation</span>
        </div>

        {/* Main Heading requested by User */}
        <h1 className="text-4xl sm:text-6xl font-black tracking-tight text-white leading-tight">
          Welcome to <br className="hidden sm:inline" />
          <span className="bg-gradient-to-r from-brand-400 via-purple-400 to-cyan-400 bg-clip-text text-transparent">
            RAG Search
          </span>
        </h1>

        {/* Informative Subtitle about RAG Search */}
        <p className="text-sm sm:text-base md:text-lg text-dark-300 max-w-2xl leading-relaxed">
          Transform your PDF documents into an interactive AI knowledge base. 
          RAG Search combines vector embeddings with Google Gemini to deliver fast, accurate answers strictly backed by inline page citations.
        </p>

        {/* Primary Action Call to Action */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center items-center pt-4 w-full sm:w-auto">
          <Link 
            to="/login" 
            className="w-full sm:w-auto px-8 py-3.5 bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-400 text-white rounded-2xl font-bold text-sm shadow-xl shadow-brand-500/30 transition-all duration-200 flex items-center justify-center space-x-2.5 group"
          >
            <span>Get Started</span>
            <ArrowRight className="h-4 w-4 group-hover:translate-x-1 transition-transform" />
          </Link>
        </div>

        {/* Quick Highlights Pills */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-8 max-w-3xl w-full text-left">
          <div className="bg-dark-900/60 border border-dark-800 p-3 rounded-xl flex items-center space-x-2.5">
            <Search className="h-4 w-4 text-brand-400 shrink-0" />
            <span className="text-xs font-semibold text-dark-200">Semantic Search</span>
          </div>
          <div className="bg-dark-900/60 border border-dark-800 p-3 rounded-xl flex items-center space-x-2.5">
            <Zap className="h-4 w-4 text-amber-400 shrink-0" />
            <span className="text-xs font-semibold text-dark-200">Fast Vector Match</span>
          </div>
          <div className="bg-dark-900/60 border border-dark-800 p-3 rounded-xl flex items-center space-x-2.5">
            <Layers className="h-4 w-4 text-cyan-400 shrink-0" />
            <span className="text-xs font-semibold text-dark-200">Exact Citations</span>
          </div>
          <div className="bg-dark-900/60 border border-dark-800 p-3 rounded-xl flex items-center space-x-2.5">
            <Lock className="h-4 w-4 text-emerald-400 shrink-0" />
            <span className="text-xs font-semibold text-dark-200">Private & Secure</span>
          </div>
        </div>

      </section>

      {/* RAG Information & Architecture Cards Section */}
      <section className="bg-dark-900/40 border-t border-dark-850 py-16 px-4">
        <div className="max-w-6xl mx-auto space-y-10">
          
          <div className="text-center space-y-2">
            <h2 className="text-2xl sm:text-3xl font-extrabold text-white">How RAG Search Works</h2>
            <p className="text-dark-400 text-xs sm:text-sm max-w-xl mx-auto">
              Our enterprise pipeline indexes your documents locally and feeds verified context directly to LLMs.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
            {features.map((feature, idx) => {
              const Icon = feature.icon;
              return (
                <div key={idx} className="glass max-w-none p-6 rounded-2xl space-y-4 border border-dark-800 hover:border-brand-500/40 transition-all duration-300 hover:-translate-y-1 shadow-lg">
                  <div className={`h-10 w-10 rounded-xl flex items-center justify-center border shrink-0 ${feature.color}`}>
                    <Icon className="h-5 w-5" />
                  </div>
                  <h3 className="text-sm font-bold text-white leading-snug">{feature.title}</h3>
                  <p className="text-xs text-dark-400 leading-relaxed">{feature.desc}</p>
                </div>
              );
            })}
          </div>

        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-dark-900 h-16 flex items-center px-4 md:px-8 bg-dark-950">
        <div className="max-w-7xl w-full mx-auto flex flex-col sm:flex-row items-center justify-between text-xs text-dark-500 space-y-2 sm:space-y-0">
          <span>&copy; {new Date().getFullYear()} RAG Search Engine. All rights reserved.</span>
          <div className="flex items-center space-x-4">
            <span className="flex items-center space-x-1.5 text-dark-400">
              <ShieldCheck className="h-4 w-4 text-emerald-400" />
              <span>ChromaDB + Gemini RAG Engine</span>
            </span>
          </div>
        </div>
      </footer>

    </div>
  );
};

export default LandingPage;
