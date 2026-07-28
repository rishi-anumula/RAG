import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { 
  ArrowLeft, 
  FileText, 
  Layers, 
  Sparkles, 
  Search, 
  Copy, 
  Check, 
  RefreshCw, 
  MessageSquare, 
  AlertCircle,
  Cpu,
  BookOpen,
  Download
} from 'lucide-react';
import { documentService } from '../services/documentService';
import type { Document } from '../types';

interface ChunkItem {
  id: string;
  document_id: string;
  page_number: number;
  chunk_number: number;
  content: string;
  filename: string;
}

export const DocumentOutput: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [document, setDocument] = useState<Document | null>(null);
  const [chunks, setChunks] = useState<ChunkItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedPage, setSelectedPage] = useState<number | 'all'>('all');
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const fetchOutput = async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const data = await documentService.getOutput(id);
      setDocument(data.document);
      setChunks(data.chunks);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load document output analysis.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOutput();
  }, [id]);

  const handleCopy = (content: string, chunkId: string) => {
    navigator.clipboard.writeText(content);
    setCopiedId(chunkId);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // Get unique page numbers
  const pageNumbers = Array.from(new Set(chunks.map(c => c.page_number))).sort((a, b) => a - b);

  const handleDownloadPdf = () => {
    if (!document || chunks.length === 0) return;

    const printWindow = window.open('', '_blank');
    if (!printWindow) {
      alert('Pop-up blocked! Please allow pop-ups for this site to download the PDF.');
      return;
    }

    const htmlContent = `
      <!DOCTYPE html>
      <html>
        <head>
          <title>${document.name} - Extracted Output Summary</title>
          <style>
            @page { size: A4; margin: 15mm; }
            body {
              font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
              color: #0f172a;
              line-height: 1.6;
              padding: 0;
              margin: 0;
            }
            .header {
              border-bottom: 2px solid #6366f1;
              padding-bottom: 12px;
              margin-bottom: 20px;
            }
            .title {
              font-size: 22px;
              font-weight: 800;
              color: #0f172a;
              margin: 0 0 4px 0;
            }
            .subtitle {
              font-size: 12px;
              color: #64748b;
              margin: 0;
            }
            .meta-grid {
              display: grid;
              grid-template-columns: repeat(4, 1fr);
              gap: 10px;
              margin-bottom: 20px;
              background-color: #f8fafc;
              padding: 12px;
              border-radius: 8px;
              border: 1px solid #e2e8f0;
            }
            .meta-item {
              display: flex;
              flex-direction: column;
            }
            .meta-label {
              font-size: 9px;
              text-transform: uppercase;
              font-weight: 700;
              color: #64748b;
            }
            .meta-value {
              font-size: 12px;
              font-weight: 700;
              color: #0f172a;
              margin-top: 2px;
            }
            .section-title {
              font-size: 15px;
              font-weight: 700;
              color: #4f46e5;
              margin: 20px 0 10px 0;
              border-bottom: 1px solid #e2e8f0;
              padding-bottom: 4px;
            }
            .chunk-card {
              background: #ffffff;
              border: 1px solid #cbd5e1;
              border-radius: 6px;
              padding: 12px;
              margin-bottom: 12px;
              page-break-inside: avoid;
            }
            .chunk-header {
              display: flex;
              justify-content: space-between;
              font-size: 10px;
              font-weight: 700;
              color: #475569;
              margin-bottom: 6px;
              background: #f1f5f9;
              padding: 4px 8px;
              border-radius: 4px;
            }
            .chunk-content {
              font-size: 11px;
              color: #334155;
              white-space: pre-wrap;
            }
            .footer {
              margin-top: 25px;
              font-size: 9px;
              color: #94a3b8;
              text-align: center;
              border-top: 1px solid #e2e8f0;
              padding-top: 8px;
            }
          </style>
        </head>
        <body>
          <div class="header">
            <h1 class="title">${document.name}</h1>
            <p class="subtitle">AI Knowledge Base RAG Search — Processed Document Output Report</p>
          </div>

          <div class="meta-grid">
            <div class="meta-item">
              <span class="meta-label">File Size</span>
              <span class="meta-value">${formatFileSize(document.size)}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">Total Chunks</span>
              <span class="meta-value">${chunks.length} Chunks</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">Total Pages</span>
              <span class="meta-value">${pageNumbers.length} Pages</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">Status</span>
              <span class="meta-value" style="color: #059669; text-transform: uppercase;">${document.status}</span>
            </div>
          </div>

          <h2 class="section-title">Extracted Document Output Content</h2>

          ${chunks.map((c) => `
            <div class="chunk-card">
              <div class="chunk-header">
                <span>PAGE ${c.page_number} — CHUNK #${c.chunk_number + 1}</span>
                <span>${c.content.length} characters</span>
              </div>
              <div class="chunk-content">${c.content.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</div>
            </div>
          `).join('')}

          <div class="footer">
            Generated on ${new Date().toLocaleString()} — AI Knowledge Base Search System
          </div>

          <script>
            window.onload = function() {
              window.print();
            };
          </script>
        </body>
      </html>
    `;

    printWindow.document.write(htmlContent);
    printWindow.document.close();
  };

  // Filter chunks based on search query and selected page
  const filteredChunks = chunks.filter(chunk => {
    const matchesPage = selectedPage === 'all' || chunk.page_number === selectedPage;
    const matchesSearch = searchQuery.trim() === '' || 
      chunk.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
      `page ${chunk.page_number}`.includes(searchQuery.toLowerCase());
    return matchesPage && matchesSearch;
  });

  return (
    <div className="space-y-6 pb-12">
      {/* Top Header Navigation */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 glass p-6 rounded-2xl border border-dark-800">
        <div className="flex items-center space-x-4">
          <button
            onClick={() => navigate('/documents')}
            className="p-2.5 bg-dark-800/80 hover:bg-dark-700 text-dark-300 hover:text-white rounded-xl transition-all border border-dark-700/50"
            title="Back to Documents"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <div className="flex items-center space-x-3">
              <h1 className="text-xl font-bold text-white truncate max-w-md">
                {document?.name || 'Document Output Analysis'}
              </h1>
              {document && (
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider ${
                  document.status === 'processed' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                  document.status === 'processing' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                  document.status === 'failed' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' :
                  'bg-brand-500/10 text-brand-400 border border-brand-500/20'
                }`}>
                  {document.status}
                </span>
              )}
            </div>
            <p className="text-xs text-dark-400 mt-1">
              Extracted text chunks, page breakdown, and vector index details
            </p>
          </div>
        </div>

        {/* Header Action Buttons */}
        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={fetchOutput}
            className="px-3.5 py-2 bg-dark-800 hover:bg-dark-750 text-dark-200 hover:text-white rounded-xl text-xs font-semibold transition-all border border-dark-700 flex items-center space-x-2"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>

          <button
            onClick={handleDownloadPdf}
            disabled={!document || chunks.length === 0}
            className="px-3.5 py-2 bg-emerald-600/10 hover:bg-emerald-600/20 disabled:opacity-50 text-emerald-400 rounded-xl text-xs font-semibold transition-all border border-emerald-500/20 flex items-center space-x-2"
            title="Download extracted document summary report as PDF"
          >
            <Download className="h-4 w-4" />
            <span>Download PDF Summary</span>
          </button>

          <Link
            to="/chat"
            className="px-4 py-2 bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-400 text-white rounded-xl text-xs font-semibold shadow-lg shadow-brand-500/20 transition-all flex items-center space-x-2"
          >
            <MessageSquare className="h-4 w-4" />
            <span>Query in AI Chat</span>
          </Link>
        </div>
      </div>

      {/* Loading Skeleton */}
      {loading ? (
        <div className="glass p-12 rounded-2xl text-center space-y-4">
          <div className="inline-block p-4 rounded-full bg-brand-500/10 text-brand-400 animate-pulse">
            <RefreshCw className="h-8 w-8 animate-spin" />
          </div>
          <p className="text-sm font-medium text-dark-300">Extracting document output and vector chunks...</p>
        </div>
      ) : error ? (
        <div className="glass p-8 rounded-2xl text-center space-y-4 border border-rose-500/20 bg-rose-500/5">
          <AlertCircle className="h-10 w-10 text-rose-400 mx-auto" />
          <h3 className="text-base font-bold text-white">Error Loading Output</h3>
          <p className="text-xs text-rose-300 max-w-md mx-auto">{error}</p>
          <button
            onClick={fetchOutput}
            className="px-4 py-2 bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 rounded-xl text-xs font-semibold transition-all border border-rose-500/30"
          >
            Try Again
          </button>
        </div>
      ) : (
        <>
          {/* Metadata Analytics Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="glass p-5 rounded-2xl border border-dark-800 flex items-center space-x-4">
              <div className="h-12 w-12 rounded-xl bg-brand-500/10 flex items-center justify-center text-brand-400">
                <FileText className="h-6 w-6" />
              </div>
              <div>
                <p className="text-xs font-medium text-dark-400">File Size</p>
                <p className="text-base font-bold text-white mt-0.5">
                  {document ? formatFileSize(document.size) : 'N/A'}
                </p>
              </div>
            </div>

            <div className="glass p-5 rounded-2xl border border-dark-800 flex items-center space-x-4">
              <div className="h-12 w-12 rounded-xl bg-emerald-500/10 flex items-center justify-center text-emerald-400">
                <Layers className="h-6 w-6" />
              </div>
              <div>
                <p className="text-xs font-medium text-dark-400">Total Chunks</p>
                <p className="text-base font-bold text-white mt-0.5">
                  {chunks.length} Text Segments
                </p>
              </div>
            </div>

            <div className="glass p-5 rounded-2xl border border-dark-800 flex items-center space-x-4">
              <div className="h-12 w-12 rounded-xl bg-purple-500/10 flex items-center justify-center text-purple-400">
                <BookOpen className="h-6 w-6" />
              </div>
              <div>
                <p className="text-xs font-medium text-dark-400">Total Pages</p>
                <p className="text-base font-bold text-white mt-0.5">
                  {pageNumbers.length} {pageNumbers.length === 1 ? 'Page' : 'Pages'}
                </p>
              </div>
            </div>

            <div className="glass p-5 rounded-2xl border border-dark-800 flex items-center space-x-4">
              <div className="h-12 w-12 rounded-xl bg-cyan-500/10 flex items-center justify-center text-cyan-400">
                <Cpu className="h-6 w-6" />
              </div>
              <div>
                <p className="text-xs font-medium text-dark-400">Vector Embeddings</p>
                <p className="text-base font-bold text-white mt-0.5 truncate">
                  384d Dense Vector
                </p>
              </div>
            </div>
          </div>

          {/* Search & Filter Bar */}
          <div className="glass p-4 rounded-2xl border border-dark-800 flex flex-col md:flex-row items-center justify-between gap-4">
            {/* Search Input */}
            <div className="relative flex-1 w-full">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-dark-400" />
              <input
                type="text"
                placeholder="Search extracted text content across all pages..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 bg-dark-900/60 border border-dark-750 focus:border-brand-500 rounded-xl text-xs text-white placeholder-dark-500 focus:outline-none transition-all"
              />
            </div>

            {/* Page Selector Tabs */}
            <div className="flex items-center space-x-2 overflow-x-auto w-full md:w-auto pb-1 md:pb-0">
              <button
                onClick={() => setSelectedPage('all')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all shrink-0 ${
                  selectedPage === 'all'
                    ? 'bg-brand-600 text-white shadow-md shadow-brand-500/10'
                    : 'bg-dark-800 text-dark-400 hover:text-white hover:bg-dark-750'
                }`}
              >
                All Pages ({chunks.length})
              </button>
              {pageNumbers.map(page => {
                const count = chunks.filter(c => c.page_number === page).length;
                return (
                  <button
                    key={page}
                    onClick={() => setSelectedPage(page)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all shrink-0 ${
                      selectedPage === page
                        ? 'bg-brand-600 text-white shadow-md shadow-brand-500/10'
                        : 'bg-dark-800 text-dark-400 hover:text-white hover:bg-dark-750'
                    }`}
                  >
                    Page {page} ({count})
                  </button>
                );
              })}
            </div>
          </div>

          {/* Extracted Output Content List */}
          <div className="space-y-4">
            <div className="flex items-center justify-between px-1">
              <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                <Sparkles className="h-4 w-4 text-brand-400" />
                <span>Extracted Document Output ({filteredChunks.length})</span>
              </h3>
              {searchQuery && (
                <span className="text-xs text-brand-400">
                  Showing results for "{searchQuery}"
                </span>
              )}
            </div>

            {filteredChunks.length === 0 ? (
              <div className="glass p-12 rounded-2xl text-center space-y-3 border border-dark-800">
                <FileText className="h-10 w-10 text-dark-500 mx-auto" />
                <p className="text-sm font-medium text-dark-300">No extracted text matches your filter.</p>
                <button
                  onClick={() => { setSearchQuery(''); setSelectedPage('all'); }}
                  className="px-3.5 py-1.5 bg-dark-800 hover:bg-dark-750 text-brand-400 rounded-lg text-xs font-semibold transition-all"
                >
                  Clear Filters
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-4">
                {filteredChunks.map((chunk, idx) => (
                  <div 
                    key={chunk.id || idx}
                    className="glass p-5 rounded-2xl border border-dark-800 hover:border-dark-700 transition-all space-y-3 group"
                  >
                    {/* Chunk Header */}
                    <div className="flex items-center justify-between border-b border-dark-800/60 pb-3">
                      <div className="flex items-center space-x-3">
                        <span className="px-2.5 py-1 rounded-lg bg-brand-500/10 text-brand-400 font-mono text-xs font-bold border border-brand-500/20">
                          Page {chunk.page_number}
                        </span>
                        <span className="text-xs font-medium text-dark-400 font-mono">
                          Chunk #{chunk.chunk_number + 1}
                        </span>
                        <span className="text-xs text-dark-500">
                          ({chunk.content.length} characters)
                        </span>
                      </div>

                      <button
                        onClick={() => handleCopy(chunk.content, chunk.id || `${idx}`)}
                        className="p-1.5 bg-dark-800 hover:bg-dark-700 text-dark-400 hover:text-white rounded-lg transition-all border border-dark-750 flex items-center space-x-1 text-xs"
                        title="Copy text chunk"
                      >
                        {copiedId === (chunk.id || `${idx}`) ? (
                          <>
                            <Check className="h-3.5 w-3.5 text-emerald-400" />
                            <span className="text-emerald-400 font-medium">Copied</span>
                          </>
                        ) : (
                          <>
                            <Copy className="h-3.5 w-3.5" />
                            <span>Copy</span>
                          </>
                        )}
                      </button>
                    </div>

                    {/* Chunk Content */}
                    <div className="bg-dark-950/70 p-4 rounded-xl border border-dark-850 font-sans text-xs text-dark-200 leading-relaxed whitespace-pre-wrap select-text">
                      {chunk.content}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};
export default DocumentOutput;
