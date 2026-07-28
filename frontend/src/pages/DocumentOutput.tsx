import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { jsPDF } from 'jspdf';
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

    try {
      const pdf = new jsPDF();
      const pageWidth = pdf.internal.pageSize.getWidth();
      const margin = 15;
      const maxLineWidth = pageWidth - margin * 2;

      // Header Banner
      pdf.setFillColor(99, 102, 241);
      pdf.rect(0, 0, pageWidth, 26, 'F');

      pdf.setTextColor(255, 255, 255);
      pdf.setFontSize(14);
      pdf.setFont('helvetica', 'bold');
      pdf.text('AI KNOWLEDGE BASE — FULL DOCUMENT REPORT', margin, 17);

      // Metadata Overview
      let y = 38;
      pdf.setFontSize(12);
      pdf.setTextColor(15, 23, 42);
      pdf.setFont('helvetica', 'bold');
      pdf.text(`Document: ${document.name}`, margin, y);

      y += 7;
      pdf.setFontSize(9.5);
      pdf.setTextColor(100, 116, 139);
      pdf.setFont('helvetica', 'normal');
      pdf.text(`Size: ${formatFileSize(document.size)}  |  Total Chunks: ${chunks.length}  |  Total Pages: ${pageNumbers.length}  |  Status: ${document.status.toUpperCase()}`, margin, y);

      y += 10;
      pdf.setDrawColor(226, 232, 240);
      pdf.setLineWidth(0.5);
      pdf.line(margin, y, pageWidth - margin, y);

      y += 10;

      // Chunks Iteration
      chunks.forEach((chunk) => {
        if (y > 250) {
          pdf.addPage();
          y = 20;
        }

        // Chunk Badge
        pdf.setFillColor(241, 245, 249);
        pdf.rect(margin, y, maxLineWidth, 8, 'F');
        pdf.setFontSize(9);
        pdf.setFont('helvetica', 'bold');
        pdf.setTextColor(71, 85, 105);
        pdf.text(`PAGE ${chunk.page_number}  —  CHUNK #${chunk.chunk_number + 1} (${chunk.content.length} chars)`, margin + 4, y + 5.5);

        y += 12;
        pdf.setFontSize(9);
        pdf.setFont('helvetica', 'normal');
        pdf.setTextColor(30, 41, 59);

        const lines = pdf.splitTextToSize(chunk.content, maxLineWidth);
        lines.forEach((line: string) => {
          if (y > 275) {
            pdf.addPage();
            y = 20;
          }
          pdf.text(line, margin, y);
          y += 5;
        });

        y += 8;
      });

      // Footer
      const pageCount = pdf.internal.pages.length - 1;
      for (let i = 1; i <= pageCount; i++) {
        pdf.setPage(i);
        pdf.setFontSize(8);
        pdf.setTextColor(148, 163, 184);
        pdf.text(`Generated on ${new Date().toLocaleDateString()} — Page ${i} of ${pageCount}`, margin, 287);
      }

      const safeDocName = document.name.replace(/[^a-zA-Z0-9_-]/g, '_');
      pdf.save(`${safeDocName}_Summary_Report.pdf`);
    } catch (err) {
      console.error('Failed to generate full document PDF:', err);
      alert('Failed to generate PDF summary file.');
    }
  };

  const handleDownloadSingleChunkPdf = (chunk: ChunkItem) => {
    if (!document) return;

    try {
      const pdf = new jsPDF();
      const pageWidth = pdf.internal.pageSize.getWidth();
      const margin = 15;
      const maxLineWidth = pageWidth - margin * 2;

      // Primary Header
      pdf.setFillColor(99, 102, 241);
      pdf.rect(0, 0, pageWidth, 24, 'F');

      pdf.setTextColor(255, 255, 255);
      pdf.setFontSize(14);
      pdf.setFont('helvetica', 'bold');
      pdf.text('AI KNOWLEDGE BASE — CHUNK REPORT', margin, 15);

      // Metadata Table
      let y = 35;
      pdf.setFontSize(11);
      pdf.setTextColor(15, 23, 42);
      pdf.setFont('helvetica', 'bold');
      pdf.text(`Document: ${document.name}`, margin, y);

      y += 7;
      pdf.setFontSize(9);
      pdf.setTextColor(100, 116, 139);
      pdf.setFont('helvetica', 'normal');
      pdf.text(`Page Number: ${chunk.page_number}  |  Chunk Index: #${chunk.chunk_number + 1}  |  Length: ${chunk.content.length} characters`, margin, y);

      y += 10;
      pdf.setDrawColor(226, 232, 240);
      pdf.setLineWidth(0.5);
      pdf.line(margin, y, pageWidth - margin, y);

      // Content Title
      y += 10;
      pdf.setFontSize(11);
      pdf.setFont('helvetica', 'bold');
      pdf.setTextColor(79, 70, 229);
      pdf.text('EXTRACTED TEXT CONTENT:', margin, y);

      // Content Body
      y += 8;
      pdf.setFontSize(9.5);
      pdf.setFont('helvetica', 'normal');
      pdf.setTextColor(30, 41, 59);

      const splitText = pdf.splitTextToSize(chunk.content, maxLineWidth);
      
      splitText.forEach((line: string) => {
        if (y > 275) {
          pdf.addPage();
          y = 20;
        }
        pdf.text(line, margin, y);
        y += 5.5;
      });

      // Footer
      const pageCount = pdf.internal.pages.length - 1;
      for (let i = 1; i <= pageCount; i++) {
        pdf.setPage(i);
        pdf.setFontSize(8);
        pdf.setTextColor(148, 163, 184);
        pdf.text(`Generated on ${new Date().toLocaleDateString()} — Page ${i} of ${pageCount}`, margin, 287);
      }

      const safeDocName = document.name.replace(/[^a-zA-Z0-9_-]/g, '_');
      const filename = `${safeDocName}_p${chunk.page_number}_chunk${chunk.chunk_number + 1}.pdf`;
      pdf.save(filename);
    } catch (err) {
      console.error('Failed to generate chunk PDF:', err);
      alert('Failed to generate PDF file.');
    }
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

                      <div className="flex items-center space-x-2">
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

                        <button
                          onClick={() => handleDownloadSingleChunkPdf(chunk)}
                          className="p-1.5 bg-emerald-600/10 hover:bg-emerald-600/20 text-emerald-400 hover:text-emerald-300 rounded-lg transition-all border border-emerald-500/20 flex items-center space-x-1 text-xs font-semibold"
                          title="Download this specific chunk as PDF"
                        >
                          <Download className="h-3.5 w-3.5" />
                          <span>Chunk PDF</span>
                        </button>
                      </div>
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
